from __future__ import annotations

from dataclasses import replace

import numpy as np

from app.optimization.explain_hooks import (
    compute_explanation_hooks,
    excluded_stock_diagnostics,
    marginal_return_contributions,
    marginal_risk_contributions,
)


def test_euler_risk_components_sum_to_total_variance(golden_problem) -> None:
    weights = np.asarray([0.15, 0.20, 0.25, 0.20, 0.20])
    components, shares = marginal_risk_contributions(
        golden_problem.symbols, golden_problem.covariance, weights
    )
    variance = float(weights @ golden_problem.covariance @ weights)
    assert np.isclose(sum(components.values()), variance, atol=1e-12)
    assert np.isclose(sum(shares.values()), 1.0, atol=1e-12)


def test_return_contributions_sum_to_portfolio_return(golden_problem) -> None:
    weights = np.full(5, 0.2)
    contributions = marginal_return_contributions(
        golden_problem.symbols, golden_problem.expected_returns, weights
    )
    assert np.isclose(sum(contributions.values()), golden_problem.expected_returns @ weights)


def test_excluded_diagnostics_cover_all_categories(golden_problem) -> None:
    weights = np.asarray([0.2, 0.4, 0.2, 0.0, 0.2])
    diagnostics = excluded_stock_diagnostics(golden_problem, weights)
    assert diagnostics["INFY"] == "sector-cap-blocked"

    dominated_problem = replace(
        golden_problem,
        expected_returns=np.asarray([0.20, 0.16, 0.13, 0.17, 0.11]),
        covariance=np.diag(np.asarray([0.10, 0.18, 0.16, 0.21, 0.14]) ** 2),
        sectors=("Energy", "IT", "Financials", "Energy", "FMCG"),
    )
    dominated = excluded_stock_diagnostics(
        dominated_problem, np.asarray([0.3, 0.2, 0.2, 0.0, 0.3])
    )
    assert dominated["INFY"] == "dominated"


def test_zero_variance_has_zero_normalized_risk_shares(golden_problem) -> None:
    zero_covariance = replace(golden_problem, covariance=np.zeros((5, 5)))
    hooks = compute_explanation_hooks(zero_covariance, np.full(5, 0.2), {"C1": 1.5})
    assert sum(hooks.normalized_risk_shares.values()) == 0
    assert hooks.shadow_prices == {"C1": 1.5}

