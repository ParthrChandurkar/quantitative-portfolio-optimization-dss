from __future__ import annotations

import numpy as np
import pytest

from app.analytics.risk_metrics import (
    build_risk_metrics,
    historical_var_95,
    maximum_drawdown,
    parametric_var_95,
    realized_annualized_volatility,
    sharpe_ratio,
)


def test_risk_formulas_match_known_analytical_answers() -> None:
    assert sharpe_ratio(0.12, 0.02, 0.20) == pytest.approx(0.5)
    assert realized_annualized_volatility(np.asarray([0.01, -0.01]), 2) == pytest.approx(
        0.02
    )
    assert maximum_drawdown(np.asarray([100.0, 120.0, 90.0, 108.0])) == pytest.approx(
        -0.25
    )
    assert parametric_var_95(100_000.0, 0.10, 0.20) == pytest.approx(22_900.0)
    returns = np.asarray([-0.10, -0.05, 0.0, 0.05, 0.10])
    assert historical_var_95(100_000.0, returns) == pytest.approx(9_000.0)


def test_combined_metrics_show_model_and_realized_risk_side_by_side() -> None:
    metrics = build_risk_metrics(
        budget=100_000.0,
        weights=np.asarray([0.5, 0.5]),
        expected_returns=np.asarray([0.10, 0.14]),
        covariance=np.diag([0.04, 0.04]),
        risk_free_rate=0.02,
        backtest_returns=np.asarray([0.01, -0.02, 0.03]),
        backtest_values=np.asarray([100_000.0, 101_000.0, 98_980.0, 101_949.4]),
    )
    assert metrics.model_annualized_volatility == pytest.approx(np.sqrt(0.02))
    assert metrics.realized_annualized_volatility > 0
    assert metrics.max_drawdown < 0
    assert np.isfinite(metrics.historical_var_95)


def test_zero_volatility_sharpe_and_short_series() -> None:
    assert sharpe_ratio(0.02, 0.02, 0.0) == 0.0
    assert np.isinf(sharpe_ratio(0.03, 0.02, 0.0))
    assert realized_annualized_volatility(np.asarray([0.01])) == 0.0


def test_risk_functions_reject_invalid_shapes_and_values() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        sharpe_ratio(0.1, 0.02, -0.1)
    with pytest.raises(ValueError, match="non-empty"):
        maximum_drawdown(np.asarray([]))
    with pytest.raises(ValueError, match="positive"):
        maximum_drawdown(np.asarray([100.0, 0.0]))
    with pytest.raises(ValueError, match="non-empty"):
        historical_var_95(100.0, np.asarray([]))
