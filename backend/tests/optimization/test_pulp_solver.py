from __future__ import annotations

from dataclasses import replace

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from app.optimization.constraints import check_all_constraints
from app.optimization.pulp_solver import _return_scenarios, solve_mad
from app.optimization.types import OptimizationInput, OptimizationStatus


def test_golden_mad_solution_obeys_c1_through_c6_and_binds_it_cap(golden_problem) -> None:
    """Golden FR-4 test from the specification."""

    result = solve_mad(golden_problem)
    weights = result.weight_vector(golden_problem.symbols)
    assert result.status is OptimizationStatus.OPTIMAL
    assert all(report.is_satisfied for report in result.constraint_reports)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert np.all((weights >= -1e-6) & (weights <= 0.4 + 1e-6))
    assert weights[1] + weights[3] <= 0.40 + 1e-6
    assert np.isclose(weights[1] + weights[3], 0.40, atol=1e-6)
    assert np.count_nonzero(weights > 1e-6) >= 4
    assert "C4_SectorCap_IT" in result.metadata["shadow_prices"]


@given(
    asset_count=st.integers(min_value=5, max_value=9),
    minimum=st.integers(min_value=3, max_value=4),
)
@settings(max_examples=10, deadline=None)
def test_random_feasible_mad_portfolios_respect_all_constraints(
    asset_count: int, minimum: int
) -> None:
    """Property test for C1-C7 over randomly sized feasible universes."""

    rng = np.random.default_rng(asset_count * 100 + minimum)
    returns = rng.uniform(0.10, 0.20, asset_count)
    volatility = rng.uniform(0.12, 0.25, asset_count)
    problem = OptimizationInput(
        symbols=tuple(f"S{index}" for index in range(asset_count)),
        expected_returns=returns,
        covariance=np.diag(volatility**2),
        sectors=tuple(f"Sector{index % 3}" for index in range(asset_count)),
        budget=1_000_000,
        target_return=float(np.min(returns)),
        max_single_weight=0.4,
        default_sector_cap=1.0,
        min_holdings=minimum,
        max_holdings=asset_count,
        min_lot_weight=0.01,
    )
    result = solve_mad(problem)
    assert result.status is OptimizationStatus.OPTIMAL
    weights = result.weight_vector(problem.symbols)
    assert all(report.is_satisfied for report in check_all_constraints(problem, weights))


def test_mad_uses_supplied_historical_returns(golden_problem) -> None:
    history = np.tile(golden_problem.expected_returns / 252, (20, 1))
    problem = replace(golden_problem, historical_returns=history)
    assert np.array_equal(_return_scenarios(problem), history)


def test_structural_infeasibility_is_structured(golden_problem) -> None:
    problem = replace(
        golden_problem, min_holdings=2, max_holdings=2, max_single_weight=0.4
    )
    result = solve_mad(problem)
    assert result.status is OptimizationStatus.INFEASIBLE
    assert result.weights == {}
    assert "C1/C3/C6" in result.message
