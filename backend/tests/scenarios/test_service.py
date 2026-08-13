from __future__ import annotations

from dataclasses import replace

import numpy as np

from app.optimization.constraints import check_all_constraints
from app.scenarios.service import run_scenario
from app.scenarios.types import ScenarioType


def test_full_budget_scenario_resolves_and_regenerates_explanations(golden_problem) -> None:
    result = run_scenario(
        golden_problem,
        ScenarioType.BUDGET_INCREASE,
        {"new_budget": 5_000_000},
    )
    assert result.metadata["re_solved"] is True
    assert result.metadata["shock_applied_to"] == "optimization_inputs"
    assert result.transformed_inputs.budget == 5_000_000
    assert result.simulated_result.is_feasible
    weights = result.simulated_result.weight_vector(golden_problem.symbols)
    assert all(
        report.is_satisfied
        for report in check_all_constraints(result.transformed_inputs, weights)
    )
    assert result.explanations is not None
    assert result.explanations.included
    assert result.comparison is not None
    assert np.isclose(sum(item.delta_w for item in result.comparison.holdings), 0.0)
    assert result.lot_feasibility_changed is True
    assert result.scale_change_explanation is not None


def test_continuous_budget_change_is_explicitly_pure_scale(golden_problem) -> None:
    continuous = replace(golden_problem, min_holdings=None, max_holdings=None)
    result = run_scenario(
        continuous,
        ScenarioType.BUDGET_INCREASE,
        {"new_budget": 5_000_000},
    )
    assert result.weights_unchanged is True
    assert result.lot_feasibility_changed is False
    assert result.pure_scale_change is True
    assert "only INR allocations scale" in (result.scale_change_explanation or "")


def test_inflation_exposes_nominal_and_real_expected_return(golden_problem) -> None:
    result = run_scenario(
        golden_problem,
        ScenarioType.INFLATION,
        {"delta_pi": 0.005},
    )
    assert result.simulated_result.is_feasible
    assert result.nominal_expected_return == result.simulated_result.expected_return
    assert result.inflation_adjusted_expected_return == (
        (1 + result.nominal_expected_return) / 1.005 - 1
    )
    assert result.explanations is not None


def test_risk_profile_scenario_uses_new_variance_ceiling(golden_problem) -> None:
    result = run_scenario(
        golden_problem,
        ScenarioType.RISK_PROFILE_CHANGE,
        {"risk_tolerance": 0.16},
    )
    assert result.transformed_inputs.risk_tolerance == 0.16
    assert result.transformed_inputs.target_return is None
    assert result.metadata["sigma_max_sq"] == 0.16**2
    assert result.simulated_result.is_feasible
