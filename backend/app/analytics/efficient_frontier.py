"""Efficient-frontier sweep backed by the Phase 4 SciPy QP solver."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from app.optimization.scipy_solver import solve_continuous
from app.optimization.types import (
    ConstraintReport,
    OptimizationInput,
    OptimizationResult,
    SolverName,
)


@dataclass(frozen=True, slots=True)
class FrontierPoint:
    target_return: float
    expected_return: float
    volatility: float
    weights: dict[str, float]
    constraint_reports: tuple[ConstraintReport, ...]


def _loose_volatility_ceiling(problem: OptimizationInput) -> float:
    largest_asset_volatility = float(
        np.sqrt(max(float(np.max(np.diag(problem.covariance))), 0.0))
    )
    return max(largest_asset_volatility * 1.01, 1e-6)


def _require_feasible(result: OptimizationResult, purpose: str) -> OptimizationResult:
    if not result.is_feasible:
        raise ValueError(f"cannot construct efficient frontier: {purpose}: {result.message}")
    return result


def build_efficient_frontier(
    problem: OptimizationInput, point_count: int = 30
) -> tuple[FrontierPoint, ...]:
    """Sweep feasible return floors and reuse ``solve_continuous`` for every point."""

    if point_count < 2:
        raise ValueError("point_count must be at least 2")
    lowest_floor = float(np.min(problem.expected_returns))
    minimum_variance_problem = replace(
        problem,
        target_return=lowest_floor,
        solver=SolverName.SCIPY,
    )
    minimum_result = _require_feasible(
        solve_continuous(minimum_variance_problem), "minimum-variance endpoint failed"
    )
    maximum_return_problem = replace(
        problem,
        target_return=None,
        risk_tolerance=problem.risk_tolerance or _loose_volatility_ceiling(problem),
        solver=SolverName.SCIPY,
    )
    maximum_result = _require_feasible(
        solve_continuous(maximum_return_problem), "maximum-return endpoint failed"
    )
    assert minimum_result.expected_return is not None
    assert maximum_result.expected_return is not None
    lower = minimum_result.expected_return
    upper = maximum_result.expected_return
    if upper < lower - 1e-8:
        raise ValueError("cannot construct efficient frontier: invalid feasible range")

    points: list[FrontierPoint] = []
    previous_return = -np.inf
    previous_volatility = -np.inf
    for target in np.linspace(lower, upper, point_count):
        sweep_problem = replace(
            problem,
            target_return=float(target),
            solver=SolverName.SCIPY,
        )
        result = solve_continuous(sweep_problem)
        if not result.is_feasible:
            continue
        assert result.expected_return is not None
        assert result.expected_volatility is not None
        # SLSQP noise can create sub-micro-unit reversals. Retain the genuine
        # Pareto curve while discarding numerically dominated duplicates.
        if result.expected_return + 1e-7 < previous_return:
            continue
        if result.expected_volatility + 1e-7 < previous_volatility:
            continue
        points.append(
            FrontierPoint(
                target_return=float(target),
                expected_return=result.expected_return,
                volatility=result.expected_volatility,
                weights=result.weights,
                constraint_reports=result.constraint_reports,
            )
        )
        previous_return = result.expected_return
        previous_volatility = result.expected_volatility
    if len(points) < 2:
        raise ValueError("cannot construct efficient frontier: fewer than two feasible points")
    return tuple(points)
