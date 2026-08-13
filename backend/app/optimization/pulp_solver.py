"""Mixed-integer Konno-Yamazaki mean absolute deviation portfolio solver."""

from __future__ import annotations

from time import perf_counter

import numpy as np
import pulp

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


def _return_scenarios(problem: OptimizationInput) -> FloatArray:
    """Use observed returns or deterministic covariance-consistent synthetic shocks."""

    if problem.historical_returns is not None:
        return np.asarray(problem.historical_returns, dtype=float)
    eigenvalues, eigenvectors = np.linalg.eigh(problem.covariance)
    root = eigenvectors @ np.diag(np.sqrt(np.clip(eigenvalues, 0.0, None)))
    shocks = np.sqrt(problem.asset_count) * root.T
    return np.vstack(
        (problem.expected_returns + shocks, problem.expected_returns - shocks)
    )


def add_c1_budget(model: pulp.LpProblem, weights: list[pulp.LpVariable]) -> None:
    model += pulp.lpSum(weights) == 1.0, "C1_Budget"


def add_c2_non_negativity(
    model: pulp.LpProblem, weights: list[pulp.LpVariable]
) -> None:
    for index, weight in enumerate(weights):
        model += weight >= 0.0, f"C2_NonNegativity_{index}"


def add_c3_max_weight(
    model: pulp.LpProblem, weights: list[pulp.LpVariable], maximum: float
) -> None:
    for index, weight in enumerate(weights):
        model += weight <= maximum, f"C3_MaxWeight_{index}"


def add_c4_sector_caps(
    model: pulp.LpProblem,
    weights: list[pulp.LpVariable],
    problem: OptimizationInput,
) -> None:
    for sector in sorted(set(problem.sectors)):
        indices = [index for index, value in enumerate(problem.sectors) if value == sector]
        model += (
            pulp.lpSum(weights[index] for index in indices) <= problem.sector_cap(sector),
            f"C4_SectorCap_{sector}",
        )


def add_c6_cardinality(
    model: pulp.LpProblem,
    included: list[pulp.LpVariable],
    minimum: int,
    maximum: int,
) -> None:
    model += pulp.lpSum(included) >= minimum, "C6_CardinalityMin"
    model += pulp.lpSum(included) <= maximum, "C6_CardinalityMax"


def add_c7_linking(
    model: pulp.LpProblem,
    weights: list[pulp.LpVariable],
    included: list[pulp.LpVariable],
    minimum_lot: float,
    maximum: float,
) -> None:
    for index, (weight, flag) in enumerate(zip(weights, included, strict=True)):
        model += weight >= minimum_lot * flag, f"C7_LinkMin_{index}"
        model += weight <= maximum * flag, f"C7_LinkMax_{index}"


def _build_mad_model(
    problem: OptimizationInput, *, relax_binary: bool = False
) -> tuple[pulp.LpProblem, list[pulp.LpVariable], list[pulp.LpVariable]]:
    model = pulp.LpProblem("OptiVest_Konno_Yamazaki_MAD", pulp.LpMinimize)
    n_assets = problem.asset_count
    weights = [pulp.LpVariable(f"w_{index}") for index in range(n_assets)]
    category = "Continuous" if relax_binary else "Binary"
    included = [pulp.LpVariable(f"y_{index}", lowBound=0, upBound=1, cat=category) for index in range(n_assets)]

    add_c1_budget(model, weights)
    add_c2_non_negativity(model, weights)
    add_c3_max_weight(model, weights, problem.max_single_weight)
    add_c4_sector_caps(model, weights, problem)
    add_c6_cardinality(
        model,
        included,
        problem.min_holdings or 1,
        problem.max_holdings or n_assets,
    )
    add_c7_linking(
        model, weights, included, problem.min_lot_weight, problem.max_single_weight
    )
    if problem.target_return is not None:
        model += (
            pulp.lpSum(
                float(problem.expected_returns[index]) * weights[index]
                for index in range(n_assets)
            )
            >= problem.target_return,
            "TargetReturnFloor",
        )

    scenarios = _return_scenarios(problem)
    centered = scenarios - np.mean(scenarios, axis=0)
    deviations = [
        pulp.LpVariable(f"deviation_{period}", lowBound=0)
        for period in range(scenarios.shape[0])
    ]
    for period, deviation in enumerate(deviations):
        expression = pulp.lpSum(
            float(centered[period, asset]) * weights[asset] for asset in range(n_assets)
        )
        model += deviation >= expression, f"MAD_Positive_{period}"
        model += deviation >= -expression, f"MAD_Negative_{period}"

    mad = pulp.lpSum(deviations) / scenarios.shape[0]
    if problem.target_return is not None:
        model += mad
    else:
        # With a risk ceiling, maximize return while bounding linearized MAD by the
        # volatility tolerance. Both values are annualized decimal rates.
        assert problem.risk_tolerance is not None
        model += mad <= problem.risk_tolerance, "C5_MAD_RiskCeiling"
        model.sense = pulp.LpMaximize
        model.setObjective(
            pulp.lpSum(
                float(problem.expected_returns[index]) * weights[index]
                for index in range(n_assets)
            )
        )
    return model, weights, included


def _relaxation_shadow_prices(problem: OptimizationInput) -> dict[str, float]:
    model, _, _ = _build_mad_model(problem, relax_binary=True)
    model.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=problem.time_limit_seconds))
    return {
        name: float(constraint.pi)
        for name, constraint in model.constraints.items()
        if constraint.pi is not None
    }


def solve_mad(problem: OptimizationInput) -> OptimizationResult:
    """Solve a cardinality-constrained MAD model with CBC."""

    started = perf_counter()
    conflict = find_structural_infeasibility(problem)
    if conflict is not None:
        return OptimizationResult(
            OptimizationStatus.INFEASIBLE,
            SolverName.PULP,
            {},
            None,
            None,
            None,
            None,
            int((perf_counter() - started) * 1000),
            message=conflict,
        )
    model, variables, included_variables = _build_mad_model(problem)
    model.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=problem.time_limit_seconds))
    elapsed = int((perf_counter() - started) * 1000)
    status_name = pulp.LpStatus[model.status]
    status_map = {
        "Optimal": OptimizationStatus.OPTIMAL,
        "Infeasible": OptimizationStatus.INFEASIBLE,
        "Not Solved": OptimizationStatus.TIME_LIMIT,
        "Undefined": OptimizationStatus.FAILED,
        "Unbounded": OptimizationStatus.FAILED,
    }
    status = status_map.get(status_name, OptimizationStatus.FAILED)
    if status is not OptimizationStatus.OPTIMAL:
        return OptimizationResult(
            status,
            SolverName.PULP,
            {},
            None,
            None,
            None,
            None,
            elapsed,
            message=f"CBC status: {status_name}",
        )
    weights = np.asarray([pulp.value(variable) or 0.0 for variable in variables], dtype=float)
    included = np.asarray(
        [pulp.value(variable) or 0.0 for variable in included_variables], dtype=float
    )
    reports = check_all_constraints(problem, weights, included)
    variance = float(weights @ problem.covariance @ weights)
    expected_return = float(problem.expected_returns @ weights)
    shadow_prices = _relaxation_shadow_prices(problem)
    return OptimizationResult(
        OptimizationStatus.OPTIMAL,
        SolverName.PULP,
        dict(zip(problem.symbols, weights.tolist(), strict=True)),
        float(pulp.value(model.objective)),
        expected_return,
        variance,
        float(np.sqrt(max(variance, 0.0))),
        elapsed,
        reports,
        message=f"CBC status: {status_name}",
        metadata={
            "risk_measure": "Konno-Yamazaki mean absolute deviation",
            "included": included.tolist(),
            "shadow_prices": shadow_prices,
        },
    )

