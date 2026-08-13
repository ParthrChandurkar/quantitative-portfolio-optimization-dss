from __future__ import annotations

from dataclasses import replace

import pytest

from app.explainability.service import build_explanations
from app.optimization.engine import solve
from app.optimization.types import OptimizationResult, OptimizationStatus, SolverName


def test_service_builds_frontend_and_persistence_compatible_bundle(golden_problem) -> None:
    result = solve(golden_problem)
    bundle = build_explanations(result)
    assert bundle.included
    assert len(bundle.included) >= 4
    assert bundle.notable_exclusions
    assert bundle.constraint_insights
    assert bundle.diversification.overall_score > 0
    assert all(item.decision == "included" for item in bundle.included)
    assert all(item.rationale == item.narrative_text for item in bundle.included)
    assert all(0 <= item.model_score <= 100 for item in bundle.included)
    repeated = build_explanations(result)
    assert bundle == repeated


def test_service_can_mark_forced_inclusion_categories(golden_problem) -> None:
    result = solve(golden_problem)
    context = dict(result.metadata["explainability_context"])
    included = next(symbol for symbol, weight in result.weights.items() if weight > 1e-6)
    context["cardinality_floor_symbols"] = [included]
    amended = replace(result, metadata={**result.metadata, "explainability_context": context})
    bundle = build_explanations(amended)
    item = next(item for item in bundle.included if item.symbol == included)
    assert item.primary_reason.value == "cardinality_floor"


def test_service_rejects_failed_or_contextless_results(golden_problem) -> None:
    failed = OptimizationResult(
        OptimizationStatus.FAILED,
        SolverName.SCIPY,
        {},
        None,
        None,
        None,
        None,
        1,
    )
    with pytest.raises(ValueError, match="feasible result"):
        build_explanations(failed)
    solved = solve(golden_problem)
    with pytest.raises(TypeError, match="lacks explainability_context"):
        build_explanations(replace(solved, metadata={}))
