from __future__ import annotations

import numpy as np
import pytest

from app.explainability.diversification_score import calculate_diversification_score


def test_single_stock_portfolio_has_minimum_score() -> None:
    result = calculate_diversification_score(np.asarray([1.0]), ("Energy",))
    assert result.stock_concentration_hhi == 1.0
    assert result.sector_concentration_hhi == 1.0
    assert result.overall_score == 0.0


def test_equal_weights_across_ten_sectors_score_near_100() -> None:
    result = calculate_diversification_score(
        np.full(10, 0.1), tuple(f"Sector {index}" for index in range(10))
    )
    assert np.isclose(result.stock_concentration_hhi, 0.1)
    assert np.isclose(result.sector_concentration_hhi, 0.1)
    assert np.isclose(result.overall_score, 90.0)
    assert result.overall_score > 85


@pytest.mark.parametrize(
    ("weights", "sectors"),
    [(np.asarray([0.5]), ("A", "B")), (np.asarray([0.5, -0.5]), ("A", "B"))],
)
def test_invalid_weights_are_rejected(weights, sectors) -> None:
    with pytest.raises(ValueError):
        calculate_diversification_score(weights, sectors)

