from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from app.optimization.constraints import (
    c3_max_single_weight,
    c5_risk_ceiling,
    c6_cardinality,
    c7_linking,
    find_structural_infeasibility,
    target_return_floor,
)
from app.optimization.types import (
    OptimizationInput,
    OptimizationResult,
    OptimizationStatus,
    SolverName,
)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"symbols": ("A", "A", "C", "D", "E")}, "symbols must be unique"),
        ({"sectors": ("A",)}, "sectors must align"),
        ({"expected_returns": np.ones(4)}, "expected_returns"),
        ({"covariance": np.eye(4)}, "covariance"),
        ({"historical_returns": np.ones((4, 4))}, "historical_returns"),
        ({"budget": 0}, "budget"),
        ({"max_single_weight": 0}, "max_single_weight"),
        ({"min_lot_weight": 0.9}, "min_lot_weight"),
        ({"target_return": None, "risk_tolerance": None}, "target_return or risk_tolerance"),
        ({"target_return": None, "risk_tolerance": 0}, "risk_tolerance"),
        ({"min_holdings": 0}, "min_holdings"),
        ({"max_holdings": 0}, "max_holdings"),
        ({"min_holdings": 5, "max_holdings": 4}, "cannot exceed"),
    ],
)
def test_input_contract_rejects_invalid_shapes_and_bounds(
    golden_problem: OptimizationInput, changes: dict, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(golden_problem, **changes)


def test_input_contract_rejects_empty_universe() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        OptimizationInput((), np.asarray([]), np.empty((0, 0)), (), 1, target_return=0.1)


def test_constraint_negative_paths_and_structural_conflicts(golden_problem) -> None:
    weights = np.asarray([0.8, 0.05, 0.05, 0.05, 0.05])
    assert not c3_max_single_weight(weights, 0.4).is_satisfied
    assert not c5_risk_ceiling(weights, golden_problem.covariance, 0.05).is_satisfied
    assert not c6_cardinality(np.asarray([1.0, 0.0, 0.0, 0.0, 0.0]), 4, 5).is_satisfied
    assert not c7_linking(weights, np.ones(5), 0.1, 0.4).is_satisfied
    assert not target_return_floor(weights, golden_problem.expected_returns, 0.2).is_satisfied

    too_many = replace(golden_problem, min_holdings=6, max_holdings=6)
    assert "available universe" in (find_structural_infeasibility(too_many) or "")
    excessive_lots = replace(golden_problem, min_lot_weight=0.3, min_holdings=4)
    assert "min_lot_weight" in (find_structural_infeasibility(excessive_lots) or "")


def test_result_helpers() -> None:
    result = OptimizationResult(
        OptimizationStatus.OPTIMAL,
        SolverName.SCIPY,
        {"A": 1.0},
        0.1,
        0.1,
        0.2,
        0.2**0.5,
        1,
    )
    assert result.is_feasible
    assert np.array_equal(result.weight_vector(("A", "B")), np.asarray([1.0, 0.0]))
