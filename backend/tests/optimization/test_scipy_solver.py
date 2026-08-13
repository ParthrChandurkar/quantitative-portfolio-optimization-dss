from __future__ import annotations

from dataclasses import replace

import numpy as np

from app.optimization.constraints import (
    c1_budget,
    c2_non_negativity,
    c3_max_single_weight,
    c4_sector_caps,
    c5_risk_ceiling,
)
from app.optimization.scipy_solver import (
    build_c1_budget_constraint,
    build_c4_sector_constraints,
    build_c5_risk_constraint,
    build_target_return_constraint,
    portfolio_return,
    portfolio_variance,
    solve_continuous,
)
from app.optimization.types import OptimizationStatus


def test_continuous_minimum_variance_with_return_floor(golden_problem) -> None:
    problem = replace(golden_problem, min_holdings=None, max_holdings=None)
    result = solve_continuous(problem)
    weights = result.weight_vector(problem.symbols)
    assert result.status is OptimizationStatus.OPTIMAL
    assert result.expected_return >= 0.14 - 1e-6
    assert all(report.is_satisfied for report in result.constraint_reports)
    assert c1_budget(weights).is_satisfied
    assert c2_non_negativity(weights).is_satisfied
    assert c3_max_single_weight(weights, 0.4).is_satisfied
    assert all(
        item.is_satisfied
        for item in c4_sector_caps(weights, problem.sectors, {"IT": 0.4}, 1.0)
    )
    assert portfolio_return(weights, problem.expected_returns) == result.expected_return
    assert portfolio_variance(weights, problem.covariance) == result.expected_variance


def test_continuous_max_return_with_risk_ceiling(golden_problem) -> None:
    problem = replace(
        golden_problem,
        target_return=None,
        risk_tolerance=0.16,
        min_holdings=None,
        max_holdings=None,
    )
    result = solve_continuous(problem)
    weights = result.weight_vector(problem.symbols)
    assert result.status is OptimizationStatus.OPTIMAL
    assert c5_risk_ceiling(weights, problem.covariance, 0.16).is_satisfied
    assert build_c5_risk_constraint(problem) is not None
    assert build_target_return_constraint(problem) is None


def test_scipy_named_constraint_builders(golden_problem) -> None:
    weights = np.full(5, 0.2)
    assert build_c1_budget_constraint()["fun"](weights) == 0
    assert len(build_c4_sector_constraints(golden_problem)) == 4
    assert build_target_return_constraint(golden_problem) is not None
    assert build_c5_risk_constraint(golden_problem) is None


def test_restricted_support_detects_insufficient_capacity(golden_problem) -> None:
    result = solve_continuous(golden_problem, support_indices=(0, 1))
    assert result.status is OptimizationStatus.INFEASIBLE
    assert "selected support" in result.message

