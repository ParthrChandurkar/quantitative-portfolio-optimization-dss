"""Continuous constrained quadratic portfolio solver using SciPy SLSQP."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import numpy as np
from scipy.optimize import OptimizeResult, minimize

from app.optimization.constraints import (
    check_all_constraints,
    find_structural_infeasibility,
)
from app.optimization.types import (
    FloatArray,
    OptimizationInput,
    OptimizationResult,
    OptimizationStatus,
    SolverName,
)


def portfolio_variance(weights: FloatArray, covariance: FloatArray) -> float:
    return float(weights @ covariance @ weights)


def portfolio_return(weights: FloatArray, expected_returns: FloatArray) -> float:
    return float(expected_returns @ weights)


def build_c1_budget_constraint() -> dict[str, Any]:
    """C1 equality definition consumed by SLSQP."""

    return {"type": "eq", "fun": lambda weights: float(np.sum(weights) - 1.0)}


def build_c4_sector_constraints(problem: OptimizationInput) -> list[dict[str, Any]]:
    """C4 inequality definitions, one per sector."""

    sectors = np.asarray(problem.sectors)
    constraints: list[dict[str, Any]] = []
    for sector in sorted(set(problem.sectors)):
        mask = sectors == sector
        cap = problem.sector_cap(sector)
        constraints.append(
            {
                "type": "ineq",
                "fun": lambda weights, mask=mask, cap=cap: float(
                    cap - np.sum(weights[mask])
                ),
            }
        )
    return constraints


def build_c5_risk_constraint(problem: OptimizationInput) -> dict[str, Any] | None:
    """C5 variance-ceiling definition when risk tolerance is configured."""

    if problem.risk_tolerance is None:
        return None
    ceiling = problem.risk_tolerance**2
    return {
        "type": "ineq",
        "fun": lambda weights: ceiling - portfolio_variance(weights, problem.covariance),
    }


def build_target_return_constraint(problem: OptimizationInput) -> dict[str, Any] | None:
    if problem.target_return is None:
        return None
    return {
        "type": "ineq",
        "fun": lambda weights: portfolio_return(weights, problem.expected_returns)
        - problem.target_return,
    }


def _initial_weights(problem: OptimizationInput, support: FloatArray) -> FloatArray:
    count = int(np.count_nonzero(support))
    weights = np.zeros(problem.asset_count, dtype=float)
    if count:
        weights[support] = 1.0 / count
    return weights


def solve_continuous(
    problem: OptimizationInput,
    *,
    support_indices: tuple[int, ...] | None = None,
    enforce_min_lot: bool = False,
) -> OptimizationResult:
    """Solve min-variance with return floor, or max-return with risk ceiling."""

    started = perf_counter()
    conflict = find_structural_infeasibility(problem)
    if conflict is not None:
        return OptimizationResult(
            status=OptimizationStatus.INFEASIBLE,
            solver_used=SolverName.SCIPY,
            weights={},
            objective_value=None,
            expected_return=None,
            expected_variance=None,
            expected_volatility=None,
            solve_time_ms=int((perf_counter() - started) * 1000),
            message=conflict,
        )

    support = np.ones(problem.asset_count, dtype=bool)
    if support_indices is not None:
        support[:] = False
        support[np.asarray(support_indices, dtype=int)] = True
        if np.count_nonzero(support) * problem.max_single_weight < 1 - 1e-6:
            return OptimizationResult(
                status=OptimizationStatus.INFEASIBLE,
                solver_used=SolverName.SCIPY,
                weights={},
                objective_value=None,
                expected_return=None,
                expected_variance=None,
                expected_volatility=None,
                solve_time_ms=int((perf_counter() - started) * 1000),
                message="C1/C3/C6 conflict: selected support cannot fund the portfolio",
            )

    lower = np.where(support, problem.min_lot_weight if enforce_min_lot else 0.0, 0.0)
    upper = np.where(support, problem.max_single_weight, 0.0)
    constraints: list[dict[str, Any]] = [
        build_c1_budget_constraint(),
        *build_c4_sector_constraints(problem),
    ]
    target = build_target_return_constraint(problem)
    risk = build_c5_risk_constraint(problem)
    if target is not None:
        constraints.append(target)
    if risk is not None:
        constraints.append(risk)

    if problem.target_return is not None:
        objective = lambda weights: portfolio_variance(weights, problem.covariance)
    else:
        objective = lambda weights: -portfolio_return(weights, problem.expected_returns)

    result: OptimizeResult = minimize(
        objective,
        _initial_weights(problem, support),
        method="SLSQP",
        bounds=list(zip(lower, upper, strict=True)),
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 2000, "disp": False},
    )
    elapsed = int((perf_counter() - started) * 1000)
    if not result.success:
        return OptimizationResult(
            status=OptimizationStatus.INFEASIBLE
            if "incompatible" in result.message.casefold()
            else OptimizationStatus.FAILED,
            solver_used=SolverName.SCIPY,
            weights={},
            objective_value=None,
            expected_return=None,
            expected_variance=None,
            expected_volatility=None,
            solve_time_ms=elapsed,
            message=str(result.message),
        )

    weights = np.where(np.abs(result.x) < 1e-10, 0.0, result.x).astype(float)
    reports = check_all_constraints(problem, weights, support.astype(float))
    if not all(report.is_satisfied for report in reports):
        return OptimizationResult(
            status=OptimizationStatus.FAILED,
            solver_used=SolverName.SCIPY,
            weights={},
            objective_value=None,
            expected_return=None,
            expected_variance=None,
            expected_volatility=None,
            solve_time_ms=elapsed,
            constraint_reports=reports,
            message="SciPy returned a point outside configured feasibility tolerance",
        )
    variance = portfolio_variance(weights, problem.covariance)
    expected_return = portfolio_return(weights, problem.expected_returns)
    multipliers = getattr(result, "multipliers", np.asarray([], dtype=float))
    return OptimizationResult(
        status=OptimizationStatus.OPTIMAL,
        solver_used=SolverName.SCIPY,
        weights=dict(zip(problem.symbols, weights.tolist(), strict=True)),
        objective_value=float(result.fun),
        expected_return=expected_return,
        expected_variance=variance,
        expected_volatility=float(np.sqrt(max(variance, 0.0))),
        solve_time_ms=elapsed,
        constraint_reports=reports,
        message=str(result.message),
        metadata={"iterations": int(result.nit), "multipliers": np.asarray(multipliers).tolist()},
    )

