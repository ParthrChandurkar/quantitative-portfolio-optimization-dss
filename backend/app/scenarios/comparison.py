"""Exact baseline-versus-scenario portfolio comparison calculations."""

from __future__ import annotations

from app.explainability.diversification_score import calculate_diversification_score
from app.optimization.types import OptimizationResult
from app.scenarios.types import (
    HoldingDelta,
    PortfolioMetrics,
    ScenarioComparison,
)


def _metrics(
    result: OptimizationResult,
    symbols: tuple[str, ...],
    sectors: tuple[str, ...],
    risk_free_rate: float,
) -> PortfolioMetrics:
    if result.expected_return is None or result.expected_volatility is None:
        raise ValueError("comparison requires feasible results with risk-return metrics")
    weights = result.weight_vector(symbols)
    diversification = calculate_diversification_score(weights, sectors)
    sharpe = (
        (result.expected_return - risk_free_rate) / result.expected_volatility
        if result.expected_volatility > 1e-15
        else 0.0
    )
    return PortfolioMetrics(
        result.expected_return,
        result.expected_volatility,
        sharpe,
        diversification.overall_score,
    )


def compare_results(
    base: OptimizationResult,
    simulated: OptimizationResult,
    symbols: tuple[str, ...],
    sectors: tuple[str, ...],
    risk_free_rate: float = 0.0,
) -> ScenarioComparison:
    """Calculate per-stock delta_w and exact simulated-minus-base metric deltas."""

    if not base.is_feasible or not simulated.is_feasible:
        raise ValueError("comparison requires two feasible optimization results")
    base_weights = base.weight_vector(symbols)
    simulated_weights = simulated.weight_vector(symbols)
    deltas = simulated_weights - base_weights
    holdings = tuple(
        HoldingDelta(
            symbol,
            float(base_weights[index]),
            float(simulated_weights[index]),
            float(deltas[index]),
            "increased"
            if deltas[index] > 1e-9
            else "decreased"
            if deltas[index] < -1e-9
            else "unchanged",
        )
        for index, symbol in enumerate(symbols)
    )
    base_metrics = _metrics(base, symbols, sectors, risk_free_rate)
    simulated_metrics = _metrics(simulated, symbols, sectors, risk_free_rate)
    return ScenarioComparison(
        holdings,
        base_metrics,
        simulated_metrics,
        simulated_metrics.expected_return - base_metrics.expected_return,
        simulated_metrics.volatility - base_metrics.volatility,
        simulated_metrics.sharpe_ratio - base_metrics.sharpe_ratio,
        simulated_metrics.diversification_score - base_metrics.diversification_score,
    )
