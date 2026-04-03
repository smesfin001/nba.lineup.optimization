from __future__ import annotations

import csv
import json
from datetime import date

from lakers_optimizer.db import SessionLocal, engine
from lakers_optimizer.ingest import ingest_team_snapshot, init_db, load_file_data_source
from lakers_optimizer.models import Lineup, Player


def _write_players_csv(path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "player_id",
                "name",
                "team",
                "position",
                "height_inches",
                "weight",
                "three_pct",
                "ts_pct",
                "ast_pct",
                "usage_rate",
                "def_rating",
                "dbpm",
                "bpm",
                "vorp",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"player_id": 1, "name": "P1", "team": "LAL", "position": "G", "height_inches": 76, "weight": 190, "three_pct": 0.4, "ts_pct": 0.58, "ast_pct": 20, "usage_rate": 21, "def_rating": 112, "dbpm": 0.3, "bpm": 1.0, "vorp": 0.5},
                {"player_id": 2, "name": "P2", "team": "LAL", "position": "G", "height_inches": 77, "weight": 195, "three_pct": 0.36, "ts_pct": 0.57, "ast_pct": 18, "usage_rate": 19, "def_rating": 111, "dbpm": 0.1, "bpm": 0.8, "vorp": 0.4},
                {"player_id": 3, "name": "P3", "team": "LAL", "position": "F", "height_inches": 79, "weight": 215, "three_pct": 0.35, "ts_pct": 0.56, "ast_pct": 14, "usage_rate": 18, "def_rating": 109, "dbpm": 0.5, "bpm": 1.2, "vorp": 0.6},
                {"player_id": 4, "name": "P4", "team": "LAL", "position": "F", "height_inches": 80, "weight": 225, "three_pct": 0.34, "ts_pct": 0.55, "ast_pct": 12, "usage_rate": 17, "def_rating": 108, "dbpm": 0.4, "bpm": 0.9, "vorp": 0.5},
                {"player_id": 5, "name": "P5", "team": "LAL", "position": "C", "height_inches": 82, "weight": 245, "three_pct": 0.29, "ts_pct": 0.6, "ast_pct": 10, "usage_rate": 22, "def_rating": 107, "dbpm": 0.9, "bpm": 1.5, "vorp": 0.7},
                {"player_id": 6, "name": "P6", "team": "LAL", "position": "F", "height_inches": 81, "weight": 230, "three_pct": 0.38, "ts_pct": 0.59, "ast_pct": 16, "usage_rate": 20, "def_rating": 110, "dbpm": 0.6, "bpm": 1.1, "vorp": 0.5},
            ]
        )


def _write_lineups_csv(path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "team",
                "player_ids",
                "net_rating",
                "offensive_rating",
                "defensive_rating",
                "minutes_played",
                "games_played",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "team": "LAL",
                "player_ids": "1,2,3,4,5",
                "net_rating": 5.2,
                "offensive_rating": 116.4,
                "defensive_rating": 111.2,
                "minutes_played": 14,
                "games_played": 3,
            }
        )


def _write_metadata_csv(path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["player", "team", "pos", "g", "mp", "ts_pct", "ast_pct", "usg_pct", "dbpm", "bpm", "vorp"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            [
                {
                    "player": "P1",
                    "team": "LAL",
                    "pos": "G",
                    "g": 99,
                    "mp": 3960,
                    "ts_pct": 0.6,
                    "ast_pct": 22,
                    "usg_pct": 30,
                    "dbpm": 1.5,
                    "bpm": 2.3,
                    "vorp": 1.1,
                },
                {
                    "player": "Ghost Player",
                    "team": "LAL",
                    "pos": "F",
                    "g": 5,
                    "mp": 142,
                    "ts_pct": 0.5,
                    "ast_pct": 1,
                    "usg_pct": 10,
                    "dbpm": -1.0,
                    "bpm": -2.2,
                    "vorp": 0.0,
                },
            ]
        )


def test_load_file_data_source_from_csv_and_ingest(tmp_path) -> None:
    players_file = tmp_path / "players.csv"
    lineups_file = tmp_path / "lineups.csv"
    _write_players_csv(players_file)
    _write_lineups_csv(lineups_file)

    source = load_file_data_source(players_path=str(players_file), lineups_path=str(lineups_file), team="LAL")
    init_db(engine)
    with SessionLocal() as session:
        summary = ingest_team_snapshot(session, team="LAL", snapshot_date=date(2026, 4, 2), source=source)
        session.commit()
        assert summary.players_upserted == 6
        assert summary.generated_lineups == 6
        assert summary.lineup_records_upserted == 6
        assert session.query(Player).count() >= 6
        assert session.query(Lineup).filter(Lineup.historical_seen.is_(True)).count() >= 1
        historical_lineup = session.query(Lineup).filter(Lineup.net_rating == 5.2).one()
        assert historical_lineup.minutes_played == 42


def test_load_file_data_source_from_bundle_json(tmp_path) -> None:
    bundle_file = tmp_path / "bundle.json"
    bundle_file.write_text(
        json.dumps(
            {
                "players": [
                    {"player_id": 1, "name": "P1", "team": "LAL", "position": "G", "height_inches": 76, "weight": 190},
                    {"player_id": 2, "name": "P2", "team": "LAL", "position": "G", "height_inches": 77, "weight": 195},
                    {"player_id": 3, "name": "P3", "team": "LAL", "position": "F", "height_inches": 79, "weight": 215},
                    {"player_id": 4, "name": "P4", "team": "LAL", "position": "F", "height_inches": 80, "weight": 225},
                    {"player_id": 5, "name": "P5", "team": "LAL", "position": "C", "height_inches": 82, "weight": 245},
                ],
                "lineups": [
                    {
                        "team": "LAL",
                        "player_ids": [1, 2, 3, 4, 5],
                        "minutes_played": 14,
                        "games_played": 3,
                        "net_rating": 2.1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    source = load_file_data_source(bundle_path=str(bundle_file), team="LAL")
    assert len(source.players) == 5
    assert source.lineups[0]["player_ids"] == [1, 2, 3, 4, 5]


def test_metadata_records_override_player_stats(tmp_path) -> None:
    players_file = tmp_path / "players.csv"
    lineups_file = tmp_path / "lineups.csv"
    metadata_file = tmp_path / "metadata.csv"
    _write_players_csv(players_file)
    _write_lineups_csv(lineups_file)
    _write_metadata_csv(metadata_file)

    source = load_file_data_source(
        players_path=str(players_file),
        lineups_path=str(lineups_file),
        metadata_path=str(metadata_file),
        team="LAL",
    )
    init_db(engine)
    with SessionLocal() as session:
        summary = ingest_team_snapshot(session, team="LAL", snapshot_date=date(2026, 4, 2), source=source)
        session.commit()
        player = session.query(Player).filter(Player.player_id == 1).one()
        assert summary.warnings
        assert any("Ghost Player" in warning for warning in summary.warnings)
        assert player.games_played == 99
        assert abs(player.minutes_per_game - (3960 / 99)) < 1e-6
        assert player.ts_pct == 0.6
