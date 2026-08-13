from __future__ import annotations

import numpy as np

from app.optimization.types import OptimizationResult, OptimizationStatus, SolverName
from app.scenarios.comparison import compare_results


def result(weights, expected_return, volatility) -> OptimizationResult:
    return OptimizationResult(
        OptimizationStatus.OPTIMAL,
        SolverName.SCIPY,
        weights,
        0.0,
        expected_return,
        volatility**2,
        volatility,
        1,
    )


def test_delta_weights_sum_zero_and_metric_deltas_are_exact() -> None:
    symbols = ("A", "B", "C")
    sectors = ("IT", "IT", "FMCG")
    base = result({"A": 0.5, "B": 0.3, "C": 0.2}, 0.14, 0.18)
    simulated = result({"A": 0.4, "B": 0.2, "C": 0.4}, 0.12, 0.15)
    comparison = compare_results(base, simulated, symbols, sectors, risk_free_rate=0.04)
    assert np.isclose(sum(item.delta_w for item in comparison.holdings), 0.0, atol=1e-15)
    assert comparison.expected_return_delta == 0.12 - 0.14
    assert comparison.volatility_delta == 0.15 - 0.18
    assert comparison.sharpe_ratio_delta == (0.12 - 0.04) / 0.15 - (0.14 - 0.04) / 0.18
    assert comparison.diversification_score_delta == (
        comparison.simulated_metrics.diversification_score
        - comparison.base_metrics.diversification_score
    )
    assert [item.direction for item in comparison.holdings] == [
        "decreased",
        "decreased",
        "increased",
    ]

