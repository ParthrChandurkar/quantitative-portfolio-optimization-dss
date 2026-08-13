from __future__ import annotations

import numpy as np
import pytest

from app.scenarios.sensitivity_tables import INFLATION_SENSITIVITY, RATE_SENSITIVITY
from app.scenarios.shock_transforms import (
    TRANSFORMS,
    apply_shock,
    budget_increase,
    budget_reduction,
    inflation,
    market_crash,
    rate_increase,
    risk_profile_change,
    sector_crash,
)
from app.scenarios.types import ScenarioType


def test_market_crash_exact_beta_and_covariance_formula(golden_problem, base_constraints) -> None:
    betas = np.asarray([1.1, 0.8, 0.9, 0.7, 0.5])
    mu, sigma, constraints = market_crash(
        golden_problem.expected_returns,
        golden_problem.covariance,
        base_constraints,
        {"delta": -0.20, "betas": betas},
    )
    assert np.array_equal(mu, golden_problem.expected_returns - 0.20 * betas)
    assert np.array_equal(sigma, golden_problem.covariance * 1.10)
    assert constraints == base_constraints


def test_rate_increase_uses_sector_sensitivity_exactly(golden_problem, base_constraints) -> None:
    delta = 0.01
    mu, sigma, _ = rate_increase(
        golden_problem.expected_returns,
        golden_problem.covariance,
        base_constraints,
        {"delta_r": delta},
    )
    expected = golden_problem.expected_returns - delta * np.asarray(
        [RATE_SENSITIVITY[sector] for sector in golden_problem.sectors]
    )
    assert np.array_equal(mu, expected)
    assert np.array_equal(sigma, golden_problem.covariance)


def test_inflation_uses_sector_sensitivity_and_exposes_delta(
    golden_problem, base_constraints
) -> None:
    delta = 0.02
    mu, sigma, constraints = inflation(
        golden_problem.expected_returns,
        golden_problem.covariance,
        base_constraints,
        {"delta_pi": delta},
    )
    expected = golden_problem.expected_returns - delta * np.asarray(
        [INFLATION_SENSITIVITY[sector] for sector in golden_problem.sectors]
    )
    assert np.array_equal(mu, expected)
    assert np.array_equal(sigma, golden_problem.covariance)
    assert constraints["inflation_delta"] == delta


def test_sector_crash_leaves_other_stocks_bit_for_bit_unchanged(
    golden_problem, base_constraints
) -> None:
    mu, sigma, _ = sector_crash(
        golden_problem.expected_returns,
        golden_problem.covariance,
        base_constraints,
        {"sector": "IT", "delta_s": -0.30},
    )
    mask = np.asarray(golden_problem.sectors) == "IT"
    assert np.array_equal(mu[~mask], golden_problem.expected_returns[~mask])
    assert np.array_equal(mu[mask], golden_problem.expected_returns[mask] - 0.30)
    assert np.array_equal(sigma, golden_problem.covariance)


def test_budget_increase_changes_only_budget_and_effective_lot(
    golden_problem, base_constraints
) -> None:
    mu, sigma, constraints = budget_increase(
        golden_problem.expected_returns,
        golden_problem.covariance,
        base_constraints,
        {"new_budget": 5_000_000},
    )
    assert np.array_equal(mu, golden_problem.expected_returns)
    assert np.array_equal(sigma, golden_problem.covariance)
    assert constraints["budget"] == 5_000_000
    assert constraints["minimum_lot_inr"] == 25_000
    assert constraints["min_lot_weight"] == 0.005
    assert constraints["lot_feasibility_changed"] is True


def test_budget_reduction_changes_only_budget_and_effective_lot(
    golden_problem, base_constraints
) -> None:
    mu, sigma, constraints = budget_reduction(
        golden_problem.expected_returns,
        golden_problem.covariance,
        base_constraints,
        {"new_budget": 1_250_000},
    )
    assert np.array_equal(mu, golden_problem.expected_returns)
    assert np.array_equal(sigma, golden_problem.covariance)
    assert constraints["budget"] == 1_250_000
    assert constraints["min_lot_weight"] == 0.02


def test_risk_profile_change_recomputes_variance_ceiling(golden_problem, base_constraints) -> None:
    mu, sigma, constraints = risk_profile_change(
        golden_problem.expected_returns,
        golden_problem.covariance,
        base_constraints,
        {"risk_tolerance": 0.18},
    )
    assert np.array_equal(mu, golden_problem.expected_returns)
    assert np.array_equal(sigma, golden_problem.covariance)
    assert constraints["risk_tolerance"] == 0.18
    assert constraints["sigma_max_sq"] == 0.18**2
    assert constraints["target_return"] is None


def test_dispatch_table_contains_exactly_seven_scenario_types(
    golden_problem, base_constraints
) -> None:
    assert set(TRANSFORMS) == set(ScenarioType)
    transformed = apply_shock(
        ScenarioType.SECTOR_CRASH,
        golden_problem.expected_returns,
        golden_problem.covariance,
        base_constraints,
        {"sector": "IT", "delta_s": -0.2},
    )
    assert transformed[0][1] == golden_problem.expected_returns[1] - 0.2


@pytest.mark.parametrize(
    ("function", "params", "message"),
    [
        (market_crash, {"delta": -0.01, "betas": np.ones(5)}, "delta"),
        (market_crash, {"delta": -0.2, "betas": np.ones(4)}, "betas"),
        (rate_increase, {"delta_r": 0.1}, "delta_r"),
        (inflation, {"delta_pi": 0.1}, "delta_pi"),
        (sector_crash, {"sector": "Unknown", "delta_s": -0.2}, "absent"),
        (budget_increase, {"new_budget": 1_000_000}, "above"),
        (budget_reduction, {"new_budget": 3_000_000}, "below"),
        (risk_profile_change, {"risk_tolerance": 0}, "positive"),
    ],
)
def test_invalid_shock_parameters_are_rejected(
    function, params, message, golden_problem, base_constraints
) -> None:
    with pytest.raises(ValueError, match=message):
        function(
            golden_problem.expected_returns,
            golden_problem.covariance,
            base_constraints,
            params,
        )

