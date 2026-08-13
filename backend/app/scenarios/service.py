"""Public transform, re-solve, explain, and compare scenario workflow."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from app.explainability.service import build_explanations
from app.optimization.engine import solve
from app.optimization.types import OptimizationInput
from app.scenarios.comparison import compare_results
from app.scenarios.shock_transforms import apply_shock
from app.scenarios.types import ScenarioResult, ScenarioType


def _constraints(problem: OptimizationInput) -> dict[str, Any]:
    return {
        "sectors": problem.sectors,
        "budget": problem.budget,
        "target_return": problem.target_return,
        "risk_tolerance": problem.risk_tolerance,
        "max_single_weight": problem.max_single_weight,
        "sector_caps": dict(problem.sector_caps),
        "default_sector_cap": problem.default_sector_cap,
        "min_holdings": problem.min_holdings,
        "max_holdings": problem.max_holdings,
        "min_lot_weight": problem.min_lot_weight,
    }


def _transformed_problem(
    base: OptimizationInput,
    mu: np.ndarray,
    sigma: np.ndarray,
    constraints: dict[str, Any],
) -> OptimizationInput:
    # Keep OptimizationInput valid and let structural checks classify an excessive
    # effective lot where the cardinality model makes it relevant.
    min_lot = min(
        float(constraints.get("min_lot_weight", base.min_lot_weight)),
        base.max_single_weight,
    )
    return replace(
        base,
        expected_returns=np.asarray(mu, dtype=float),
        covariance=np.asarray(sigma, dtype=float),
        budget=float(constraints.get("budget", base.budget)),
        target_return=constraints.get("target_return", base.target_return),
        risk_tolerance=constraints.get("risk_tolerance", base.risk_tolerance),
        min_lot_weight=min_lot,
    )


def run_scenario(
    base_inputs: OptimizationInput,
    scenario_type: ScenarioType,
    params: dict[str, Any],
) -> ScenarioResult:
    """Implement FR-6 by changing model inputs and invoking the Phase 4 solver."""

    base_result = solve(base_inputs)
    if not base_result.is_feasible:
        raise ValueError(f"base optimization is not feasible: {base_result.message}")
    mu, sigma, constraints = apply_shock(
        scenario_type,
        base_inputs.expected_returns,
        base_inputs.covariance,
        _constraints(base_inputs),
        params,
    )
    transformed = _transformed_problem(base_inputs, mu, sigma, constraints)
    simulated = solve(transformed)
    comparison = None
    explanations = None
    if simulated.is_feasible:
        comparison = compare_results(
            base_result,
            simulated,
            base_inputs.symbols,
            base_inputs.sectors,
            base_inputs.risk_free_rate,
        )
        explanations = build_explanations(simulated)

    weights_unchanged = simulated.is_feasible and np.allclose(
        base_result.weight_vector(base_inputs.symbols),
        simulated.weight_vector(base_inputs.symbols),
        atol=1e-6,
        rtol=0,
    )
    is_budget = scenario_type in {
        ScenarioType.BUDGET_INCREASE,
        ScenarioType.BUDGET_REDUCTION,
    }
    lot_changed = bool(constraints.get("lot_feasibility_changed", False)) if is_budget else False
    pure_scale = bool(is_budget and weights_unchanged and not lot_changed)
    scale_explanation: str | None = None
    if is_budget:
        if weights_unchanged and lot_changed:
            scale_explanation = (
                "Weights are unchanged, but preserving the absolute INR minimum lot changed "
                "the linking-constraint feasibility threshold."
            )
        elif pure_scale:
            scale_explanation = (
                "Weights are unchanged because the model is proportional and no minimum-lot "
                "feasibility threshold changed; only INR allocations scale with budget."
            )
        else:
            scale_explanation = (
                "Weights changed because the new INR budget altered the effective minimum-lot "
                "linking constraint."
            )

    nominal_return = simulated.expected_return
    inflation_adjusted: float | None = None
    if scenario_type is ScenarioType.INFLATION and nominal_return is not None:
        inflation_delta = float(constraints["inflation_delta"])
        inflation_adjusted = (1 + nominal_return) / (1 + inflation_delta) - 1
    return ScenarioResult(
        scenario_type,
        dict(params),
        transformed,
        base_result,
        simulated,
        comparison,
        explanations,
        nominal_return,
        inflation_adjusted,
        bool(weights_unchanged),
        pure_scale,
        lot_changed,
        scale_explanation,
        metadata={
            "re_solved": True,
            "shock_applied_to": "optimization_inputs",
            "sigma_max_sq": constraints.get("sigma_max_sq"),
            "minimum_lot_inr": constraints.get("minimum_lot_inr"),
        },
    )
