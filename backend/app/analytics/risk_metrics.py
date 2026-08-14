"""Model-estimated and historically realized portfolio risk metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.analytics.growth_projection import portfolio_moments
from app.optimization.types import FloatArray

TRADING_DAYS = 252
NORMAL_95_Z = 1.645


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    sharpe_ratio: float
    model_annualized_volatility: float
    realized_annualized_volatility: float
    max_drawdown: float
    parametric_var_95: float
    historical_var_95: float
    realized_annualized_return: float = 0.0
    realized_sharpe_ratio: float = 0.0


def sharpe_ratio(expected_return: float, risk_free_rate: float, volatility: float) -> float:
    if volatility < 0:
        raise ValueError("volatility must be non-negative")
    if volatility == 0:
        return 0.0 if expected_return == risk_free_rate else float(
            np.copysign(np.inf, expected_return - risk_free_rate)
        )
    return (expected_return - risk_free_rate) / volatility


def realized_annualized_volatility(
    periodic_returns: FloatArray, periods_per_year: int = TRADING_DAYS
) -> float:
    values = np.asarray(periodic_returns, dtype=float)
    if values.ndim != 1:
        raise ValueError("periodic_returns must be a vector")
    if values.size < 2:
        return 0.0
    return float(np.std(values, ddof=1) * np.sqrt(periods_per_year))


def realized_annualized_return(
    periodic_returns: FloatArray, periods_per_year: int = TRADING_DAYS
) -> float:
    """Geometrically annualize the observed evaluation-period returns."""

    values = np.asarray(periodic_returns, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("periodic_returns must be a non-empty vector")
    if np.any(values <= -1.0):
        raise ValueError("periodic returns must be greater than -100%")
    return float(np.prod(1.0 + values) ** (periods_per_year / values.size) - 1.0)


def maximum_drawdown(portfolio_values: FloatArray) -> float:
    values = np.asarray(portfolio_values, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("portfolio_values must be a non-empty vector")
    if np.any(values <= 0):
        raise ValueError("portfolio values must be positive")
    running_max = np.maximum.accumulate(values)
    return float(np.min((values - running_max) / running_max))


def parametric_var_95(budget: float, expected_return: float, volatility: float) -> float:
    """Parametric 95% loss amount in INR using the required annual model inputs."""

    return float(budget * (NORMAL_95_Z * volatility - expected_return))


def historical_var_95(budget: float, periodic_returns: FloatArray) -> float:
    """Empirical 95% one-period loss amount in INR."""

    values = np.asarray(periodic_returns, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("periodic_returns must be a non-empty vector")
    return float(-budget * np.quantile(values, 0.05))


def build_risk_metrics(
    budget: float,
    weights: FloatArray,
    expected_returns: FloatArray,
    covariance: FloatArray,
    risk_free_rate: float,
    backtest_returns: FloatArray,
    backtest_values: FloatArray,
) -> RiskMetrics:
    mean, model_volatility = portfolio_moments(weights, expected_returns, covariance)
    realized_return = realized_annualized_return(backtest_returns)
    realized_volatility = realized_annualized_volatility(backtest_returns)
    return RiskMetrics(
        sharpe_ratio=sharpe_ratio(mean, risk_free_rate, model_volatility),
        model_annualized_volatility=model_volatility,
        realized_annualized_volatility=realized_volatility,
        max_drawdown=maximum_drawdown(backtest_values),
        parametric_var_95=parametric_var_95(budget, mean, model_volatility),
        historical_var_95=historical_var_95(budget, backtest_returns),
        realized_annualized_return=realized_return,
        realized_sharpe_ratio=sharpe_ratio(
            realized_return, risk_free_rate, realized_volatility
        ),
    )
