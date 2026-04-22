from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from lakers_optimizer.llm import OpenAIQueryClient
from lakers_optimizer.models import Lineup
from lakers_optimizer.repository import LineupRepository, PlayerRepository
from lakers_optimizer.schemas import (
    LineupInsightResponse,
    LineupMetadataResponse,
    OptimizeLineupRequest,
    OptimizeLineupResponse,
    ParsedIntent,
    PlayerCardResponse,
    PlayerListItemResponse,
    PlayerListResponse,
    RecommendationResponse,
)
from lakers_optimizer.scoring import satisfies_constraints, score_lineup


@dataclass
class OptimizationContext:
    team: str = "LAL"


class LineupOptimizer:
    def __init__(self, session: Session, llm_client: Optional[OpenAIQueryClient] = None) -> None:
        self.session = session
        self.lineup_repo = LineupRepository(session)
        self.player_repo = PlayerRepository(session)
        self.llm_client = llm_client or OpenAIQueryClient()

    def optimize(self, request: OptimizeLineupRequest, context: Optional[OptimizationContext] = None) -> OptimizeLineupResponse:
        context = context or OptimizationContext()
        parsed_intent = self.llm_client.parse_query(
            request.query,
            {"team": context.team, "roster": self._roster_context(context.team)},
        )
        parsed_intent = self._merge_constraints(parsed_intent, request)

        lineups = self.lineup_repo.list_lineups(context.team)
        scored_historical: List[Tuple[Lineup, Dict[str, float], float]] = []
        scored_generated: List[Tuple[Lineup, Dict[str, float], float]] = []
        for lineup in lineups:
            players = self.player_repo.get_players(list(lineup.player_ids))
            if not satisfies_constraints(lineup, players, parsed_intent.constraints):
                continue
            component_scores = score_lineup(lineup, parsed_intent.weights.as_dict())
            scored_tuple = (lineup, component_scores, component_scores["final_score"])
            if lineup.historical_seen:
                scored_historical.append(scored_tuple)
            else:
                scored_generated.append(scored_tuple)

        scored_pool = scored_historical if scored_historical else scored_generated
        scored_pool.sort(key=lambda item: item[2], reverse=True)
        top_lineups = scored_pool[: request.limit]
        recommendations: List[RecommendationResponse] = []
        for rank, (lineup, component_scores, final_score) in enumerate(top_lineups, start=1):
            players = self.player_repo.get_players(list(lineup.player_ids))
            players_by_id = {player.player_id: player for player in players}
            ordered_players = [players_by_id[player_id] for player_id in lineup.player_ids if player_id in players_by_id]
            payload = {
                "player_ids": list(lineup.player_ids),
                "player_names": [player.name for player in ordered_players],
                "component_scores": component_scores,
                "trust_score": lineup.trust_score,
                "historical_seen": lineup.historical_seen,
                "score": final_score,
            }
            reasoning = self.llm_client.explain_recommendation(request.query, payload)
            recommendations.append(
                RecommendationResponse(
                    rank=rank,
                    player_ids=payload["player_ids"],
                    player_names=payload["player_names"],
                    players=[self._build_player_card(player) for player in ordered_players],
                    score=round(final_score, 4),
                    component_scores={key: round(value, 4) for key, value in component_scores.items()},
                    trust_score=round(lineup.trust_score, 4),
                    historical_seen=lineup.historical_seen,
                    lineup_metadata=LineupMetadataResponse(
                        minutes_played=lineup.minutes_played,
                        net_rating=self._round_optional(lineup.net_rating),
                        offensive_rating=self._round_optional(lineup.offensive_rating),
                        defensive_rating=self._round_optional(lineup.defensive_rating),
                        rotation_score=round(lineup.rotation_score, 4),
                    ),
                    lineup_insights=self._build_lineup_insights(lineup, component_scores, ordered_players),
                    reasoning=reasoning,
                )
            )

        return OptimizeLineupResponse(recommendations=recommendations, parsed_intent=parsed_intent)

    def list_players(self, context: Optional[OptimizationContext] = None) -> PlayerListResponse:
        context = context or OptimizationContext()
        players = self.player_repo.list_players(context.team)
        return PlayerListResponse(
            players=[
                PlayerListItemResponse(
                    player_id=player.player_id,
                    name=player.name,
                    position=player.position,
                )
                for player in players
            ]
        )

    def _merge_constraints(self, parsed_intent: ParsedIntent, request: OptimizeLineupRequest) -> ParsedIntent:
        merged = parsed_intent.model_copy(deep=True)
        include_ids: set[int] = set(merged.constraints.must_include)
        exclude_ids: set[int] = set(merged.constraints.must_exclude)
        request_include_ids = set(request.constraints.must_include)
        request_exclude_ids = set(request.constraints.must_exclude)

        if request_include_ids:
            include_ids |= request_include_ids
            exclude_ids -= request_include_ids
        if request_exclude_ids:
            exclude_ids |= request_exclude_ids
            include_ids -= request_exclude_ids

        merged.constraints.must_include = sorted(include_ids)
        merged.constraints.must_exclude = sorted(exclude_ids)
        for field_name in ("max_non_shooters", "min_size_score", "min_trust"):
            value = getattr(request.constraints, field_name)
            if value is not None:
                setattr(merged.constraints, field_name, value)
        return merged

    def _build_player_card(self, player) -> PlayerCardResponse:
        return PlayerCardResponse(
            player_id=player.player_id,
            name=player.name,
            position=player.position,
            height_inches=player.height_inches,
            minutes_per_game=self._round_optional(player.minutes_per_game),
            games_played=player.games_played,
            three_pct=self._round_optional(player.three_pct, digits=3),
            dbpm=self._round_optional(player.dbpm if player.dbpm is not None else player.bpm, digits=1),
        )

    def _build_lineup_insights(
        self,
        lineup: Lineup,
        component_scores: Dict[str, float],
        players,
    ) -> List[LineupInsightResponse]:
        metric_scores = {
            "Defense": component_scores["defense"],
            "Shooting": component_scores["shooting"],
            "Size": component_scores["size"],
            "Playmaking": component_scores["playmaking"],
        }
        top_metric = max(metric_scores.items(), key=lambda item: item[1])
        low_metric = min(metric_scores.items(), key=lambda item: item[1])
        shooting_players = sum(1 for player in players if (player.three_pct or 0.0) >= 0.35)
        insights = [
            LineupInsightResponse(
                label="Top strength",
                value="{} leads this group's profile.".format(top_metric[0]),
                tone="positive",
            ),
            LineupInsightResponse(
                label="Shooting balance",
                value="{} of 5 players clear the shooting threshold.".format(shooting_players),
                tone="positive" if shooting_players >= 3 else "neutral",
            ),
            LineupInsightResponse(
                label="Rotation trust",
                value="Rotation {:.0f}% with {} history.".format(
                    lineup.rotation_score * 100.0,
                    "real lineup minutes" if lineup.historical_seen else "generated-only evidence",
                ),
                tone="positive" if lineup.historical_seen else "neutral",
            ),
            LineupInsightResponse(
                label="Watch-out",
                value="{} is the relative weak point in this combination.".format(low_metric[0]),
                tone="caution",
            ),
        ]
        return insights

    def _round_optional(self, value: Optional[float], digits: int = 2) -> Optional[float]:
        if value is None:
            return None
        return round(value, digits)

    def _roster_context(self, team: str) -> List[Dict[str, object]]:
        return [
            {"player_id": player.player_id, "name": player.name}
            for player in self.player_repo.list_players(team)
        ]
