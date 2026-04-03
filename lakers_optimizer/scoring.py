from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from statistics import mean
from typing import Dict, List, Optional, Sequence, Tuple

from lakers_optimizer.models import Lineup, Player
from lakers_optimizer.schemas import METRIC_KEYS, QueryConstraints


DEFAULT_THREE_PCT = 0.33
DEFAULT_TS_PCT = 0.56
DEFAULT_AST_PCT = 14.0
DEFAULT_DEF_RATING = 114.0
DEFAULT_HEIGHT = 78
DEFAULT_ROTATION_SCORE = 0.1
EXPLICIT_NON_SHOOTERS = {
    "Deandre Ayton",
    "Jaxson Hayes",
    "Adou Thiero",
    "Jarred Vanderbilt",
}


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


def canonicalize_lineup(player_ids: Sequence[int]) -> Tuple[int, int, int, int, int]:
    lineup = tuple(sorted(int(player_id) for player_id in player_ids))
    if len(lineup) != 5 or len(set(lineup)) != 5:
        raise ValueError("A lineup must contain exactly 5 unique players.")
    return lineup  # type: ignore[return-value]


def generate_all_lineups(roster: List[int]) -> List[Tuple[int, int, int, int, int]]:
    return [canonicalize_lineup(list(combo)) for combo in combinations(sorted(set(roster)), 5)]


def _value_or_default(value: Optional[float], default: float) -> float:
    return float(default if value is None else value)


def compute_lineup_features(players: List[Player]) -> Dict[str, float]:
    three_pcts = [_value_or_default(player.three_pct, DEFAULT_THREE_PCT) for player in players]
    ast_pcts = [_value_or_default(player.ast_pct, DEFAULT_AST_PCT) for player in players]
    def_ratings = [_value_or_default(player.def_rating, DEFAULT_DEF_RATING) for player in players]
    heights = [_value_or_default(player.height_inches, DEFAULT_HEIGHT) for player in players]
    shooting_score = mean(three_pcts)
    spacers = len([value for value in three_pcts if value >= 0.35])
    spacing_score = shooting_score * (spacers / 5.0)
    defense_score = mean([1.0 / rating for rating in def_ratings])
    return {
        "shooting_score": shooting_score,
        "spacing_score": spacing_score,
        "defense_score": defense_score,
        "size_score": mean(heights),
        "playmaking_score": mean(ast_pcts),
    }


def compute_trust_score(minutes_played: int) -> float:
    return min(max(minutes_played, 0) / 200.0, 1.0)


def compute_player_rotation_score(player: Player) -> float:
    if player.games_played is None or player.minutes_per_game is None:
        return DEFAULT_ROTATION_SCORE
    games_component = clamp(player.games_played / 82.0)
    minutes_component = clamp(player.minutes_per_game / 36.0)
    return 0.4 * games_component + 0.6 * minutes_component


def compute_lineup_rotation_score(players: List[Player]) -> float:
    return mean([compute_player_rotation_score(player) for player in players])


@dataclass
class RankedLineup:
    lineup: Lineup
    component_scores: Dict[str, float]
    final_score: float


def score_lineup(lineup: Lineup, weights: Dict[str, float]) -> Dict[str, float]:
    raw_metrics = {
        "defense": lineup.defense_score,
        "spacing": lineup.spacing_score,
        "shooting": lineup.shooting_score,
        "size": lineup.size_score,
        "playmaking": lineup.playmaking_score,
        "rotation": lineup.rotation_score,
    }
    normalized_metrics = {
        "defense": clamp(lineup.defense_score * 100.0),
        "spacing": clamp(lineup.spacing_score),
        "shooting": clamp(lineup.shooting_score),
        "size": clamp(lineup.size_score / 100.0),
        "playmaking": clamp(lineup.playmaking_score / 100.0),
        "rotation": clamp(lineup.rotation_score),
    }
    weighted_score = sum(weights.get(key, 0.0) * normalized_metrics[key] for key in METRIC_KEYS)
    historical_quality = 0.5 if lineup.net_rating is None else clamp((lineup.net_rating + 15.0) / 30.0)
    historical_score = (
        0.7 * lineup.trust_score
        + 0.2 * historical_quality
        + 0.1 * (1.0 if lineup.historical_seen else 0.0)
    )
    final_score = 0.25 * weighted_score + 0.45 * historical_score + 0.30 * normalized_metrics["rotation"]
    return {
        "weighted_score": weighted_score,
        "historical_score": historical_score,
        "final_score": final_score,
        **raw_metrics,
    }


def count_non_shooters(players: List[Player]) -> int:
    count = 0
    for player in players:
        if player.name in EXPLICIT_NON_SHOOTERS:
            count += 1
            continue
        if player.name.startswith("P") and _value_or_default(player.three_pct, DEFAULT_THREE_PCT) < 0.33:
            count += 1
    return count


def satisfies_constraints(lineup: Lineup, players: List[Player], constraints: QueryConstraints) -> bool:
    player_ids = set(lineup.player_ids)
    if constraints.must_include and not set(constraints.must_include).issubset(player_ids):
        return False
    if constraints.must_exclude and player_ids.intersection(constraints.must_exclude):
        return False
    if constraints.max_non_shooters is not None and count_non_shooters(players) > constraints.max_non_shooters:
        return False
    if constraints.min_size_score is not None:
        minimum_height = float(constraints.min_size_score)
        for player in players:
            player_height = _value_or_default(player.height_inches, DEFAULT_HEIGHT)
            if player_height < minimum_height:
                return False
    if constraints.min_trust is not None and lineup.trust_score < constraints.min_trust:
        return False
    return True
