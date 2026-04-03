from __future__ import annotations

from lakers_optimizer.models import Lineup, Player
from lakers_optimizer.scoring import (
    canonicalize_lineup,
    compute_lineup_features,
    compute_lineup_rotation_score,
    compute_player_rotation_score,
    compute_trust_score,
    satisfies_constraints,
    score_lineup,
)
from lakers_optimizer.schemas import QueryConstraints


def build_player(player_id: int, three_pct: float, ast_pct: float, def_rating: float, height: int) -> Player:
    return Player(
        player_id=player_id,
        name="P{}".format(player_id),
        team="LAL",
        position="G",
        height_inches=height,
        weight=200,
        three_pct=three_pct,
        ts_pct=0.57,
        ast_pct=ast_pct,
        usage_rate=20.0,
        games_played=70,
        minutes_per_game=28.0,
        def_rating=def_rating,
        bpm=1.0,
        vorp=0.5,
    )


def test_compute_lineup_features_and_trust_score() -> None:
    players = [
        build_player(1, 0.40, 20.0, 110.0, 78),
        build_player(2, 0.38, 15.0, 111.0, 79),
        build_player(3, 0.36, 18.0, 109.0, 80),
        build_player(4, 0.32, 12.0, 112.0, 81),
        build_player(5, 0.29, 10.0, 108.0, 82),
    ]
    features = compute_lineup_features(players)

    assert round(features["shooting_score"], 3) == 0.35
    assert round(features["size_score"], 1) == 80.0
    assert round(compute_player_rotation_score(players[0]), 4) == 0.9015
    assert round(compute_lineup_rotation_score(players), 4) == 0.9015
    assert compute_trust_score(240) == 1.0
    assert compute_trust_score(100) == 0.5


def test_score_lineup_and_constraints() -> None:
    lineup = Lineup(
        team="LAL",
        player_1_id=1,
        player_2_id=2,
        player_3_id=3,
        player_4_id=4,
        player_5_id=5,
        shooting_score=0.35,
        spacing_score=0.21,
        defense_score=0.009,
        size_score=80.0,
        playmaking_score=16.0,
        rotation_score=0.6,
        net_rating=5.0,
        offensive_rating=115.0,
        defensive_rating=110.0,
        minutes_played=100,
        trust_score=0.5,
        historical_seen=True,
    )
    players = [
        build_player(1, 0.40, 20.0, 110.0, 78),
        build_player(2, 0.38, 15.0, 111.0, 79),
        build_player(3, 0.36, 18.0, 109.0, 80),
        build_player(4, 0.32, 12.0, 112.0, 81),
        build_player(5, 0.29, 10.0, 108.0, 82),
    ]
    scores = score_lineup(
        lineup,
        {"defense": 0.4, "spacing": 0.2, "shooting": 0.2, "size": 0.1, "playmaking": 0.1},
    )

    assert round(scores["weighted_score"], 4) == 0.568
    assert round(scores["historical_score"], 4) == 0.5833
    assert round(scores["final_score"], 4) == 0.5845
    assert satisfies_constraints(
        lineup,
        players,
        QueryConstraints(must_include=[1], max_non_shooters=2, min_size_score=78.0, min_trust=0.4),
    )
    assert not satisfies_constraints(lineup, players, QueryConstraints(min_size_score=81.0))
    assert not satisfies_constraints(lineup, players, QueryConstraints(must_exclude=[1]))


def test_canonicalize_lineup() -> None:
    assert canonicalize_lineup([5, 1, 3, 2, 4]) == (1, 2, 3, 4, 5)
