from __future__ import annotations

import numpy as np

from app.analytics.efficient_frontier import build_efficient_frontier
from app.optimization.types import OptimizationInput


def test_frontier_is_monotonic_and_each_point_is_feasible(
    analytics_universe: OptimizationInput,
) -> None:
    points = build_efficient_frontier(analytics_universe, point_count=30)
    returns = np.asarray([point.expected_return for point in points])
    risks = np.asarray([point.volatility for point in points])
    assert len(points) >= 25
    assert np.all(np.diff(returns) >= -1e-7)
    assert np.all(np.diff(risks) >= -1e-7)
    for point in points:
        assert abs(sum(point.weights.values()) - 1.0) <= 1e-6
        assert all(report.is_satisfied for report in point.constraint_reports)
        assert point.expected_return + 1e-6 >= point.target_return
