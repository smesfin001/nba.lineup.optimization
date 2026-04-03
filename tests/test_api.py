from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from lakers_optimizer.api import app
from lakers_optimizer.db import SessionLocal, engine
from lakers_optimizer.ingest import ingest_team_snapshot, init_db, load_file_data_source


def setup_module() -> None:
    init_db(engine)
    source = load_file_data_source(
        players_path="data/players_import.csv",
        lineups_path="data/lineups_import.csv",
        team="LAL",
    )
    with SessionLocal() as session:
        ingest_team_snapshot(session, team="LAL", snapshot_date=date(2026, 4, 2), source=source)
        session.commit()


def test_optimize_lineup_endpoint_returns_ranked_results() -> None:
    client = TestClient(app)
    response = client.post(
        "/optimize-lineup",
        json={
            "query": "Need defense vs fast guards but keep spacing",
            "constraints": {"must_include": [23]},
            "limit": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendations"]) == 3
    assert body["recommendations"][0]["rank"] == 1
    assert 23 in body["recommendations"][0]["player_ids"]
    assert len(body["recommendations"][0]["players"]) == 5
    assert "lineup_metadata" in body["recommendations"][0]
    assert body["recommendations"][0]["lineup_insights"]
    assert "parsed_intent" in body


def test_named_player_query_adds_must_include_constraint() -> None:
    client = TestClient(app)
    response = client.post(
        "/optimize-lineup",
        json={
            "query": "Need defense and shooting around LeBron",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert 23 in body["parsed_intent"]["constraints"]["must_include"]
    assert all(23 in recommendation["player_ids"] for recommendation in body["recommendations"])


def test_negative_named_player_query_adds_must_exclude_constraint() -> None:
    client = TestClient(app)
    response = client.post(
        "/optimize-lineup",
        json={
            "query": "Need defense and shooting, Luka is on the bench",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert 77 in body["parsed_intent"]["constraints"]["must_exclude"]
    assert all(77 not in recommendation["player_ids"] for recommendation in body["recommendations"])


def test_players_endpoint_returns_roster_options() -> None:
    client = TestClient(app)
    response = client.get("/players")

    assert response.status_code == 200
    body = response.json()
    assert body["players"]
    assert {"player_id", "name", "position"}.issubset(body["players"][0].keys())


def test_optimize_lineup_player_cards_include_dbpm_field() -> None:
    client = TestClient(app)
    response = client.post(
        "/optimize-lineup",
        json={
            "query": "Need defense and shooting around LeBron",
            "limit": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"]
    assert "dbpm" in body["recommendations"][0]["players"][0]
