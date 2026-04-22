from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field, model_validator
except ImportError:  # pragma: no cover - fallback for offline/test environments
    from ._pydantic_fallback import BaseModel, Field, model_validator


METRIC_KEYS = ("defense", "shooting", "size", "playmaking")


class IntentWeights(BaseModel):
    defense: float = 0.0
    shooting: float = 0.0
    size: float = 0.0
    playmaking: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return {key: float(getattr(self, key)) for key in METRIC_KEYS}


class QueryConstraints(BaseModel):
    must_include: List[int] = Field(default_factory=list)
    must_exclude: List[int] = Field(default_factory=list)
    max_non_shooters: Optional[int] = None
    min_size_score: Optional[float] = None
    min_trust: Optional[float] = None


class ParsedIntent(BaseModel):
    weights: IntentWeights
    constraints: QueryConstraints = Field(default_factory=QueryConstraints)


class OptimizeLineupRequest(BaseModel):
    query: str
    constraints: QueryConstraints = Field(default_factory=QueryConstraints)
    limit: int = 5

    @model_validator(mode="after")
    def validate_limit(self) -> "OptimizeLineupRequest":
        self.limit = max(1, min(self.limit, 5))
        return self


class RecommendationResponse(BaseModel):
    rank: int
    player_ids: List[int]
    player_names: List[str]
    players: List["PlayerCardResponse"]
    score: float
    component_scores: Dict[str, float]
    trust_score: float
    historical_seen: bool
    lineup_metadata: "LineupMetadataResponse"
    lineup_insights: List["LineupInsightResponse"]
    reasoning: str


class OptimizeLineupResponse(BaseModel):
    recommendations: List[RecommendationResponse]
    parsed_intent: ParsedIntent


class PlayerCardResponse(BaseModel):
    player_id: int
    name: str
    position: str
    height_inches: Optional[int] = None
    minutes_per_game: Optional[float] = None
    games_played: Optional[int] = None
    three_pct: Optional[float] = None
    dbpm: Optional[float] = None


class LineupMetadataResponse(BaseModel):
    minutes_played: int
    net_rating: Optional[float] = None
    offensive_rating: Optional[float] = None
    defensive_rating: Optional[float] = None
    rotation_score: float


class LineupInsightResponse(BaseModel):
    label: str
    value: str
    tone: str = "neutral"


class PlayerListItemResponse(BaseModel):
    player_id: int
    name: str
    position: str


class PlayerListResponse(BaseModel):
    players: List[PlayerListItemResponse]


class IngestionSummary(BaseModel):
    players_upserted: int
    lineup_records_upserted: int
    generated_lineups: int
    unmatched_player_ids: List[int] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def normalize_intent_payload(payload: Optional[Dict[str, Any]]) -> ParsedIntent:
    payload = payload or {}
    raw_weights = dict(payload.get("weights") or {})
    spacing_weight = float(raw_weights.pop("spacing", 0.0) or 0.0)
    passing_weight = float(raw_weights.pop("passing", 0.0) or 0.0)
    if spacing_weight:
        raw_weights["shooting"] = float(raw_weights.get("shooting", 0.0) or 0.0) + spacing_weight
    if passing_weight:
        raw_weights["playmaking"] = float(raw_weights.get("playmaking", 0.0) or 0.0) + passing_weight
    constraints = payload.get("constraints") or {}
    normalized = {key: float(raw_weights.get(key, 0.0) or 0.0) for key in METRIC_KEYS}
    total = sum(max(value, 0.0) for value in normalized.values())
    if total <= 0:
        normalized = {"defense": 0.3, "shooting": 0.3, "size": 0.15, "playmaking": 0.25}
    else:
        normalized = {key: max(value, 0.0) / total for key, value in normalized.items()}
    return ParsedIntent(weights=IntentWeights(**normalized), constraints=QueryConstraints(**constraints))
