from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from datetime import date
from fastapi.testclient import TestClient

import lakers_optimizer.db as db_module
import lakers_optimizer.api as api_module
from lakers_optimizer.ingest import ingest_team_snapshot, load_file_data_source
from lakers_optimizer.models import Base
import pytest


def seed_db(session) -> None:
    source = load_file_data_source(
        players_path="data/players_import.csv",
        lineups_path="data/lineups_import.csv",
        team="LAL",
    )
    ingest_team_snapshot(
        session,
        team="LAL",
        snapshot_date=date(2026, 4, 2),
        source=source,
    )
    session.commit()


@pytest.fixture
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )

    Base.metadata.create_all(bind=test_engine)

    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal)

    # Important if api.py imported SessionLocal directly:
    monkeypatch.setattr(api_module, "SessionLocal", TestingSessionLocal, raising=False)

    with TestingSessionLocal() as session:
        seed_db(session)

    with TestClient(api_module.app) as test_client:
        yield test_client

def test_optimize_lineup_endpoint_returns_ranked_results(client: TestClient) -> None:
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
    assert "spacing" not in body["parsed_intent"]["weights"]
    assert "spacing" not in body["recommendations"][0]["component_scores"]
    assert body["parsed_intent"]["weights"]["shooting"] > body["parsed_intent"]["weights"]["defense"]


def test_named_player_query_adds_must_include_constraint(client: TestClient) -> None:
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


def test_negative_named_player_query_adds_must_exclude_constraint(client: TestClient) -> None:
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


def test_passing_query_maps_to_playmaking_weight(client: TestClient) -> None:
    response = client.post(
        "/optimize-lineup",
        json={
            "query": "Need passing and ball movement around LeBron",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parsed_intent"]["weights"]["playmaking"] > body["parsed_intent"]["weights"]["shooting"]
    assert body["parsed_intent"]["weights"]["playmaking"] > body["parsed_intent"]["weights"]["defense"]


def test_players_endpoint_returns_roster_options(client: TestClient) -> None:
    response = client.get("/players")

    assert response.status_code == 200
    body = response.json()
    assert body["players"]
    assert {"player_id", "name", "position"}.issubset(body["players"][0].keys())


def test_optimize_lineup_player_cards_include_dbpm_field(client: TestClient) -> None:
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
