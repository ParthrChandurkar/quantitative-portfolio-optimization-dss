"""Transparent concentration-based diversification score."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class DiversificationScore:
    overall_score: float
    stock_concentration_hhi: float
    sector_concentration_hhi: float


def calculate_diversification_score(
    weights: NDArray[np.float64], sectors: tuple[str, ...]
) -> DiversificationScore:
    """Calculate score = 100 * [1 - .5 * (stock HHI + sector HHI)]."""

    values = np.asarray(weights, dtype=float)
    if values.ndim != 1 or values.shape[0] != len(sectors):
        raise ValueError("weights and sectors must be aligned one-dimensional values")
    if np.any(values < -1e-12) or not np.isclose(np.sum(values), 1.0, atol=1e-6):
        raise ValueError("weights must be non-negative and sum to one")
    stock_hhi = float(values @ values)
    sector_array = np.asarray(sectors)
    sector_weights = np.asarray(
        [np.sum(values[sector_array == sector]) for sector in sorted(set(sectors))]
    )
    sector_hhi = float(sector_weights @ sector_weights)
    score = float(np.clip(100 * (1 - 0.5 * (stock_hhi + sector_hhi)), 0, 100))
    return DiversificationScore(score, stock_hhi, sector_hhi)

