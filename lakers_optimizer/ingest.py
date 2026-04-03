from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from lakers_optimizer.models import Base
from lakers_optimizer.repository import LineupRepository, PlayerRepository, RosterRepository
from lakers_optimizer.schemas import IngestionSummary
from lakers_optimizer.scoring import (
    compute_lineup_features,
    compute_lineup_rotation_score,
    compute_trust_score,
    generate_all_lineups,
)


class StatsDataSource(Protocol):
    def fetch_player_stats(self, team: str) -> List[dict]:
        ...

    def fetch_lineup_stats(self, team: str) -> List[dict]:
        ...

    def fetch_player_metadata(self, team: str) -> List[dict]:
        ...

    def metadata_warnings(self) -> List[str]:
        ...


@dataclass
class StaticDataSource:
    players: List[dict]
    lineups: List[dict]
    metadata: List[dict]
    _metadata_warnings: List[str] = field(default_factory=list)

    def fetch_player_stats(self, team: str) -> List[dict]:
        return [player for player in self.players if player["team"] == team]

    def fetch_lineup_stats(self, team: str) -> List[dict]:
        return [lineup for lineup in self.lineups if lineup["team"] == team]

    def fetch_player_metadata(self, team: str) -> List[dict]:
        return [player for player in self.metadata if player["team"] == team]

    def metadata_warnings(self) -> List[str]:
        return list(self._metadata_warnings)


def _parse_optional_float(value: Any) -> Optional[float]:
    if value in (None, "", "null"):
        return None
    return float(value)


def _parse_optional_int(value: Any) -> Optional[int]:
    if value in (None, "", "null"):
        return None
    return int(value)


def _normalize_player_record(payload: Dict[str, Any], default_team: Optional[str] = None) -> dict:
    return {
        "player_id": int(payload["player_id"]),
        "name": str(payload["name"]),
        "team": str(payload.get("team") or default_team or "LAL"),
        "position": str(payload.get("position") or ""),
        "height_inches": _parse_optional_int(payload.get("height_inches")),
        "weight": _parse_optional_int(payload.get("weight")),
        "three_pct": _parse_optional_float(payload.get("three_pct")),
        "ts_pct": _parse_optional_float(payload.get("ts_pct")),
        "ast_pct": _parse_optional_float(payload.get("ast_pct")),
        "usage_rate": _parse_optional_float(payload.get("usage_rate")),
        "games_played": _parse_optional_int(payload.get("games_played")),
        "minutes_per_game": _parse_optional_float(payload.get("minutes_per_game")),
        "def_rating": _parse_optional_float(payload.get("def_rating")),
        "dbpm": _parse_optional_float(payload.get("dbpm")),
        "bpm": _parse_optional_float(payload.get("bpm")),
        "vorp": _parse_optional_float(payload.get("vorp")),
    }


def _normalize_roster_metadata(payload: Dict[str, Any], default_team: Optional[str] = None) -> dict:
    name = str(payload.get("player") or payload.get("name") or "").strip()
    return {
        "name": name,
        "team": str(payload.get("team") or default_team or "LAL"),
        "position": str(payload.get("pos") or payload.get("position") or ""),
        "games_played": _parse_optional_int(payload.get("g")),
        "minutes_total": _parse_optional_float(payload.get("mp")),
        "ts_pct": _parse_optional_float(payload.get("ts_pct")),
        "ast_pct": _parse_optional_float(payload.get("ast_pct")),
        "usage_rate": _parse_optional_float(payload.get("usg_pct")),
        "dbpm": _parse_optional_float(payload.get("dbpm")),
        "bpm": _parse_optional_float(payload.get("bpm")),
        "vorp": _parse_optional_float(payload.get("vorp")),
    }


def _normalize_metadata_records(
    records: List[dict], name_to_id: Dict[str, int], default_team: Optional[str] = None
) -> Tuple[List[dict], List[str]]:
    normalized: List[dict] = []
    warnings: List[str] = []
    for payload in records:
        metadata = _normalize_roster_metadata(payload, default_team=default_team)
        name = metadata.get("name")
        if not name:
            continue
        key = name.strip().lower()
        player_id = name_to_id.get(key)
        if player_id is None:
            warnings.append(f"Metadata row for '{name}' could not be mapped to an existing player.")
            continue
        games = metadata.get("games_played")
        minutes_total = metadata.get("minutes_total")
        minutes_per_game = None
        if minutes_total is not None and games not in (None, 0):
            minutes_per_game = minutes_total / float(games)
        normalized.append(
            {
                "player_id": player_id,
                "name": name,
                "team": metadata.get("team") or default_team or "LAL",
                "position": metadata.get("position", ""),
                "games_played": games,
                "minutes_per_game": minutes_per_game,
                "ts_pct": metadata.get("ts_pct"),
                "ast_pct": metadata.get("ast_pct"),
                "usage_rate": metadata.get("usage_rate"),
                "dbpm": metadata.get("dbpm"),
                "bpm": metadata.get("bpm"),
                "vorp": metadata.get("vorp"),
            }
        )
    return normalized, warnings


def _parse_player_ids(value: Any) -> List[int]:
    if isinstance(value, list):
        return [int(item) for item in value]
    if value in (None, ""):
        return []
    parts = str(value).replace("|", ",").split(",")
    return [int(part.strip()) for part in parts if part.strip()]


def _parse_lineup_games(payload: Dict[str, Any]) -> Optional[int]:
    for key in ("games_played", "gp"):
        if key in payload:
            return _parse_optional_int(payload.get(key))
    return None


def _normalize_lineup_record(payload: Dict[str, Any], default_team: Optional[str] = None) -> dict:
    minutes_value = payload.get("minutes_played")
    minutes_per_game = float(minutes_value) if minutes_value not in (None, "", "null") else 0.0
    games_played = _parse_lineup_games(payload)
    if minutes_per_game and games_played not in (None, 0):
        total_minutes = minutes_per_game * float(games_played)
    else:
        total_minutes = minutes_per_game
    minutes_played = int(round(total_minutes))
    return {
        "team": str(payload.get("team") or default_team or "LAL"),
        "player_ids": _parse_player_ids(payload.get("player_ids")),
        "net_rating": _parse_optional_float(payload.get("net_rating")),
        "offensive_rating": _parse_optional_float(payload.get("offensive_rating")),
        "defensive_rating": _parse_optional_float(payload.get("defensive_rating")),
        "minutes_played": minutes_played,
    }


def _load_records_from_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_records_from_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_file_data_source(
    *,
    players_path: Optional[str] = None,
    lineups_path: Optional[str] = None,
    bundle_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
    team: str = "LAL",
) -> StaticDataSource:
    raw_metadata = []
    metadata_warnings: List[str] = []

    if bundle_path:
        payload = _load_records_from_json(Path(bundle_path))
        if not isinstance(payload, dict):
            raise ValueError("Bundle JSON must be an object with 'players' and optional 'lineups' keys.")
        raw_players = payload.get("players") or []
        raw_lineups = payload.get("lineups") or []
        raw_metadata = payload.get("metadata") or []
    else:
        if not players_path:
            raise ValueError("players_path is required when bundle_path is not provided.")
        raw_players = _load_path_records(players_path)
        raw_lineups = _load_path_records(lineups_path) if lineups_path else []
        if metadata_path:
            raw_metadata = _load_path_records(metadata_path)

    if not isinstance(raw_players, list) or not isinstance(raw_lineups, list):
        raise ValueError("Players and lineups payloads must be arrays of records.")

    players = [_normalize_player_record(record, default_team=team) for record in raw_players]
    name_to_id = {
        player["name"].strip().lower(): player["player_id"]
        for player in players
        if player.get("name")
    }
    lineups = [_normalize_lineup_record(record, default_team=team) for record in raw_lineups]
    metadata, metadata_warnings = _normalize_metadata_records(raw_metadata, name_to_id, default_team=team)
    return StaticDataSource(
        players=players,
        lineups=lineups,
        metadata=metadata,
        _metadata_warnings=metadata_warnings,
    )


def _load_path_records(path_str: str) -> List[dict]:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError("File not found: {}".format(path))
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _load_records_from_csv(path)
    if suffix == ".json":
        payload = _load_records_from_json(path)
        if not isinstance(payload, list):
            raise ValueError("JSON file {} must contain an array of records.".format(path))
        return payload
    raise ValueError("Unsupported file format for {}. Use .csv or .json.".format(path))


def init_db(engine) -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    player_columns = {column["name"] for column in inspector.get_columns("players")}
    if "dbpm" not in player_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE players ADD COLUMN dbpm FLOAT"))


def ingest_team_snapshot(
    session: Session,
    team: str,
    snapshot_date: date,
    source: StatsDataSource,
) -> IngestionSummary:
    player_repo = PlayerRepository(session)
    roster_repo = RosterRepository(session)
    lineup_repo = LineupRepository(session)

    player_stats = source.fetch_player_stats(team)
    player_metadata = source.fetch_player_metadata(team)
    lineup_stats = source.fetch_lineup_stats(team)

    merged_players: Dict[int, dict] = {}
    for payload in player_stats + player_metadata:
        player_id = int(payload["player_id"])
        merged = dict(merged_players.get(player_id, {}))
        merged.update(payload)
        merged_players[player_id] = merged

    roster_player_ids = sorted(merged_players)
    lineup_repo.delete_team_lineups(team)
    roster_repo.delete_team_snapshots(team)
    players_upserted = player_repo.upsert_players(list(merged_players.values()))
    player_repo.delete_missing_team_players(team, roster_player_ids)
    roster_repo.replace_snapshot(team, snapshot_date, roster_player_ids)
    player_lookup = {player.player_id: player for player in player_repo.get_players(roster_player_ids)}

    historical_lineups = {
        tuple(sorted(record["player_ids"])): record
        for record in lineup_stats
        if len(set(record["player_ids"])) == 5
    }

    generated = generate_all_lineups(roster_player_ids)
    unmatched_player_ids: List[int] = []
    warnings: List[str] = []
    warnings.extend(source.metadata_warnings())
    lineup_records_upserted = 0

    for lineup_ids in generated:
        lineup_players = []
        for player_id in lineup_ids:
            player = player_lookup.get(player_id)
            if player is None:
                unmatched_player_ids.append(player_id)
                break
            lineup_players.append(player)
        if len(lineup_players) != 5:
            continue
        features = compute_lineup_features(lineup_players)
        rotation_score = compute_lineup_rotation_score(lineup_players)
        historical = historical_lineups.get(lineup_ids, {})
        trust_score = compute_trust_score(int(historical.get("minutes_played", 0) or 0))
        lineup_repo.upsert_lineup(
            {
                "team": team,
                "player_ids": list(lineup_ids),
                **features,
                "rotation_score": rotation_score,
                "net_rating": historical.get("net_rating"),
                "offensive_rating": historical.get("offensive_rating"),
                "defensive_rating": historical.get("defensive_rating"),
                "minutes_played": int(historical.get("minutes_played", 0) or 0),
                "trust_score": trust_score,
                "historical_seen": lineup_ids in historical_lineups,
            }
        )
        lineup_records_upserted += 1

    if len(roster_player_ids) < 5:
        warnings.append("Roster has fewer than five players; no generated lineups were created.")

    return IngestionSummary(
        players_upserted=players_upserted,
        lineup_records_upserted=lineup_records_upserted,
        generated_lineups=len(generated),
        unmatched_player_ids=sorted(set(unmatched_player_ids)),
        warnings=warnings,
    )
