from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from lakers_optimizer.config import get_settings
from lakers_optimizer.schemas import ParsedIntent, normalize_intent_payload


class OpenAIQueryClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def parse_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> ParsedIntent:
        if not self.settings.openai_api_key:
            return self._fallback_parse_query(query, context=context)
        try:
            payload = self._responses_api_request(
                instructions=(
                    "Convert a basketball lineup query into JSON with keys "
                    "'weights' and 'constraints'. Use only defense, spacing, shooting, size, playmaking weights. "
                    "If the query names a player from the provided roster context, include that player's id in "
                    "constraints.must_include unless the query explicitly excludes them."
                ),
                input_text=json.dumps({"query": query, "context": context or {}}, sort_keys=True),
            )
            return normalize_intent_payload(payload)
        except Exception:
            return self._fallback_parse_query(query, context=context)

    def explain_recommendation(self, query: str, lineup_payload: Dict[str, Any]) -> str:
        if not self.settings.openai_api_key:
            return self._fallback_explanation(query, lineup_payload)
        try:
            payload = self._responses_api_request(
                instructions="Explain in 1-2 sentences why the lineup fits the query.",
                input_text=json.dumps({"query": query, "lineup": lineup_payload}, sort_keys=True),
            )
            if isinstance(payload, dict) and isinstance(payload.get("text"), str) and payload["text"].strip():
                return payload["text"].strip()
        except Exception:
            pass
        return self._fallback_explanation(query, lineup_payload)

    def _responses_api_request(self, instructions: str, input_text: str) -> Dict[str, Any]:
        response = httpx.post(
            "{}/responses".format(self.settings.openai_base_url.rstrip("/")),
            headers={
                "Authorization": "Bearer {}".format(self.settings.openai_api_key),
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.openai_model,
                "instructions": instructions,
                "input": input_text,
                "text": {"format": {"type": "json_object"}},
            },
            timeout=10.0,
        )
        response.raise_for_status()
        body = response.json()
        output_text = body.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return json.loads(output_text)
        return {}

    def _fallback_parse_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> ParsedIntent:
        lowered = query.lower()
        weights = {
            "defense": 0.2,
            "spacing": 0.2,
            "shooting": 0.2,
            "size": 0.2,
            "playmaking": 0.2,
        }
        keyword_map = {
            "defense": ["defense", "guard", "stop", "contain", "switch"],
            "spacing": ["spacing", "shoot", "floor"],
            "shooting": ["shooting", "three", "3pt"],
            "size": ["size", "rebound", "big", "physical"],
            "playmaking": ["playmaking", "ball handling", "assist", "creation"],
        }
        for metric, keywords in keyword_map.items():
            if any(keyword in lowered for keyword in keywords):
                weights[metric] += 0.25
        constraints: Dict[str, Any] = {}
        max_non_shooters = re.search(r"max\s+(\d+)\s+non[- ]shooters", lowered)
        if max_non_shooters:
            constraints["max_non_shooters"] = int(max_non_shooters.group(1))
        include_ids, exclude_ids = self._extract_named_player_constraints(lowered, context=context)
        if include_ids:
            constraints["must_include"] = include_ids
        if exclude_ids:
            constraints["must_exclude"] = exclude_ids
        return normalize_intent_payload({"weights": weights, "constraints": constraints})

    def _extract_named_player_constraints(
        self,
        lowered_query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[int], List[int]]:
        roster = (context or {}).get("roster") or []
        include_ids: List[int] = []
        exclude_ids: List[int] = []
        negative_tokens = ("without", "exclude", "no ", "not ", "except", "sit ")

        for player in roster:
            player_id = player.get("player_id")
            if player_id is None:
                continue
            aliases = self._player_aliases(str(player.get("name") or ""))
            if not aliases:
                continue
            matched_alias = next((alias for alias in aliases if alias in lowered_query), None)
            if matched_alias is None:
                continue
            if self._is_negative_player_reference(lowered_query, matched_alias, negative_tokens):
                exclude_ids.append(int(player_id))
            else:
                include_ids.append(int(player_id))

        return sorted(set(include_ids)), sorted(set(exclude_ids))

    def _player_aliases(self, name: str) -> List[str]:
        parts = [part.strip(" .").lower() for part in name.split() if part.strip(" .")]
        aliases = {name.lower()}
        if len(parts) >= 2:
            aliases.add(parts[0])
            aliases.add(parts[-1])
            aliases.add(" ".join(parts[-2:]))
        elif parts:
            aliases.add(parts[0])
        return sorted(alias for alias in aliases if alias)

    def _is_negative_player_reference(
        self,
        lowered_query: str,
        alias: str,
        negative_tokens: tuple[str, ...],
    ) -> bool:
        if any(f"{token}{alias}" in lowered_query for token in negative_tokens):
            return True
        bench_patterns = (
            f"{alias} on the bench",
            f"{alias} is on the bench",
            f"bench {alias}",
            f"{alias} to the bench",
        )
        return any(pattern in lowered_query for pattern in bench_patterns)

    def _fallback_explanation(self, query: str, lineup_payload: Dict[str, Any]) -> str:
        metrics = lineup_payload.get("component_scores", {})
        top_metric = max(metrics.items(), key=lambda item: item[1])[0] if metrics else "balance"
        return (
            "This lineup aligns with '{}' because it rates strongest in {} while keeping trust at {:.2f}."
        ).format(query, top_metric, float(lineup_payload.get("trust_score", 0.0)))
