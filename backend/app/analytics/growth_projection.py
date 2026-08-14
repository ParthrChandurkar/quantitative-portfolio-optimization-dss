"""Deterministic portfolio growth projections and confidence bands."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.optimization.types import FloatArray


@dataclass(frozen=True, slots=True)
class GrowthPoint:
    year: int
    projected_value: float
    lower_1sigma: float
    upper_1sigma: float
    lower_2sigma: float
    upper_2sigma: float


def portfolio_moments(
    weights: FloatArray, expected_returns: FloatArray, covariance: FloatArray
) -> tuple[float, float]:
    """Return annual portfolio mean and volatility from aligned arrays."""

    vector = np.asarray(weights, dtype=float)
    means = np.asarray(expected_returns, dtype=float)
    matrix = np.asarray(covariance, dtype=float)
    if vector.ndim != 1 or means.shape != vector.shape:
        raise ValueError("weights and expected_returns must be aligned vectors")
    if matrix.shape != (vector.size, vector.size):
        raise ValueError("covariance must be square and aligned with weights")
    mean = float(vector @ means)
    variance = float(vector @ matrix @ vector)
    return mean, float(np.sqrt(max(variance, 0.0)))


def compound_value(budget: float, annual_return: float, years: int) -> float:
    """Compute ``budget * (1 + annual_return) ** years`` exactly as specified."""

    if budget <= 0:
        raise ValueError("budget in INR must be positive")
    if years < 0:
        raise ValueError("years must be non-negative")
    return float(budget * (1.0 + annual_return) ** years)


def project_growth(
    budget: float,
    weights: FloatArray,
    expected_returns: FloatArray,
    covariance: FloatArray,
    horizon_years: int,
) -> tuple[GrowthPoint, ...]:
    """Project the central value and one-/two-sigma compound bands."""

    if horizon_years < 0:
        raise ValueError("horizon_years must be non-negative")
    mean, volatility = portfolio_moments(weights, expected_returns, covariance)
    points: list[GrowthPoint] = []
    for year in range(horizon_years + 1):
        points.append(
            GrowthPoint(
                year=year,
                projected_value=compound_value(budget, mean, year),
                lower_1sigma=compound_value(budget, mean - volatility, year),
                upper_1sigma=compound_value(budget, mean + volatility, year),
                lower_2sigma=compound_value(budget, mean - 2 * volatility, year),
                upper_2sigma=compound_value(budget, mean + 2 * volatility, year),
            )
        )
    return tuple(points)
