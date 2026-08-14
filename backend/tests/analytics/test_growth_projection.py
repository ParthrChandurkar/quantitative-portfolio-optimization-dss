from __future__ import annotations

import numpy as np
import pytest

from app.analytics.growth_projection import (
    compound_value,
    portfolio_moments,
    project_growth,
)


def test_projection_starts_at_budget_and_bands_widen() -> None:
    weights = np.asarray([0.6, 0.4])
    means = np.asarray([0.10, 0.20])
    covariance = np.diag([0.01, 0.04])
    points = project_growth(100_000.0, weights, means, covariance, 8)

    assert points[0].projected_value == 100_000.0
    assert points[0].lower_1sigma == points[0].upper_2sigma == 100_000.0
    widths_1 = [point.upper_1sigma - point.lower_1sigma for point in points]
    widths_2 = [point.upper_2sigma - point.lower_2sigma for point in points]
    assert widths_1 == sorted(widths_1)
    assert widths_2 == sorted(widths_2)
    assert all(two >= one for one, two in zip(widths_1, widths_2, strict=True))


def test_projection_formula_and_portfolio_moments() -> None:
    weights = np.asarray([0.5, 0.5])
    means = np.asarray([0.08, 0.12])
    covariance = np.asarray([[0.04, 0.01], [0.01, 0.09]])
    mean, volatility = portfolio_moments(weights, means, covariance)
    assert mean == pytest.approx(0.10)
    assert volatility == pytest.approx(np.sqrt(0.0375))
    assert compound_value(1_000.0, 0.10, 2) == pytest.approx(1_210.0)


@pytest.mark.parametrize("budget,years", [(0.0, 1), (1_000.0, -1)])
def test_compound_value_rejects_invalid_inputs(budget: float, years: int) -> None:
    with pytest.raises(ValueError):
        compound_value(budget, 0.1, years)


def test_projection_rejects_misaligned_arrays_and_negative_horizon() -> None:
    with pytest.raises(ValueError, match="aligned vectors"):
        portfolio_moments(np.asarray([1.0]), np.asarray([0.1, 0.2]), np.eye(1))
    with pytest.raises(ValueError, match="horizon_years"):
        project_growth(
            1_000.0,
            np.asarray([1.0]),
            np.asarray([0.1]),
            np.asarray([[0.01]]),
            -1,
        )
