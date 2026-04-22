from typing import List, Optional

from lakers_optimizer.db import SessionLocal
from lakers_optimizer.optimizer import LineupOptimizer
from lakers_optimizer.schemas import IntentWeights, ParsedIntent, QueryConstraints, OptimizeLineupRequest


def build_parsed_intent(*, include: Optional[List[int]] = None, exclude: Optional[List[int]] = None) -> ParsedIntent:
    return ParsedIntent(
        weights=IntentWeights(),
        constraints=QueryConstraints(must_include=include or [], must_exclude=exclude or []),
    )


def build_request(*, include: Optional[List[int]] = None, exclude: Optional[List[int]] = None) -> OptimizeLineupRequest:
    return OptimizeLineupRequest(
        query="test",
        constraints=QueryConstraints(must_include=include or [], must_exclude=exclude or []),
    )


def test_request_exclude_overrides_parsed_include() -> None:
    parsed_intent = build_parsed_intent(include=[23])
    request = build_request(exclude=[23])
    with SessionLocal() as session:
        optimizer = LineupOptimizer(session=session)
        merged = optimizer._merge_constraints(parsed_intent, request)
    assert 23 not in merged.constraints.must_include
    assert merged.constraints.must_exclude == [23]


def test_request_include_overrides_parsed_exclude() -> None:
    parsed_intent = build_parsed_intent(exclude=[45])
    request = build_request(include=[45])
    with SessionLocal() as session:
        optimizer = LineupOptimizer(session=session)
        merged = optimizer._merge_constraints(parsed_intent, request)
    assert 45 in merged.constraints.must_include
    assert 45 not in merged.constraints.must_exclude


def test_request_constraints_merge_without_conflict() -> None:
    parsed_intent = build_parsed_intent(include=[5], exclude=[7])
    request = build_request(include=[6], exclude=[8])
    with SessionLocal() as session:
        optimizer = LineupOptimizer(session=session)
        merged = optimizer._merge_constraints(parsed_intent, request)
    assert set(merged.constraints.must_include) == {5, 6}
    assert set(merged.constraints.must_exclude) == {7, 8}
