from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.backtest import (
    BacktestMode,
    RebalanceFrequency,
    buy_and_hold_values,
    fetch_return_panel,
    periodic_rebalance_values,
    rebalance_schedule,
    run_backtest,
)
from app.db.models import Sector, Stock, StockPrice


def test_three_day_two_stock_series_matches_manual_calculation() -> None:
    returns = np.asarray([[0.0, 0.0], [0.10, 0.0], [0.0, 0.10]])
    weights = np.asarray([0.5, 0.5])
    observations = np.ones_like(returns, dtype=bool)

    hold_values, hold_returns = buy_and_hold_values(
        returns, weights, 100.0, observations
    )
    reset_values, reset_returns = periodic_rebalance_values(
        returns, weights, 100.0, np.asarray([False, True, True]), observations
    )

    assert hold_values == pytest.approx([100.0, 105.0, 110.0], abs=0.01)
    assert reset_values == pytest.approx([100.0, 105.0, 110.25], abs=0.01)
    assert hold_returns == pytest.approx([0.0, 0.05, 0.04761905])
    assert reset_returns == pytest.approx([0.0, 0.05, 0.05])


def test_monthly_schedule_and_late_listing_cash_handling() -> None:
    dates = (date(2025, 1, 30), date(2025, 1, 31), date(2025, 2, 3))
    assert rebalance_schedule(dates, RebalanceFrequency.MONTHLY).tolist() == [
        False,
        False,
        True,
    ]
    returns = np.asarray([[0.0, np.nan], [0.10, np.nan], [0.0, 0.20]])
    observations = np.asarray([[True, False], [True, False], [True, True]])
    values, _ = buy_and_hold_values(
        returns, np.asarray([0.5, 0.5]), 100.0, observations
    )
    assert values == pytest.approx([100.0, 105.0, 115.0])


async def test_database_backtest_aligns_gaps_and_reports_them(
    session: AsyncSession,
) -> None:
    sector = Sector(name="IT")
    first = Stock(symbol="A", company_name="A Ltd", sector=sector)
    second = Stock(symbol="B", company_name="B Ltd", sector=sector)
    session.add_all([sector, first, second])
    await session.flush()
    for stock, trade_date, daily_return in [
        (first, date(2025, 1, 2), None),
        (first, date(2025, 1, 3), Decimal("0.10")),
        (first, date(2025, 1, 6), Decimal("0.00")),
        (second, date(2025, 1, 3), None),
        (second, date(2025, 1, 6), Decimal("0.20")),
    ]:
        session.add(
            StockPrice(
                stock=stock,
                trade_date=trade_date,
                open=Decimal(100),
                high=Decimal(101),
                low=Decimal(99),
                close=Decimal(100),
                adj_close=Decimal(100),
                volume=1_000,
                daily_return=daily_return,
            )
        )
    await session.commit()

    panel = await fetch_return_panel(
        session, ("A", "B"), date(2025, 1, 2), date(2025, 1, 6)
    )
    assert panel.dates == (date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6))
    assert np.isnan(panel.returns[0, 1])
    assert any("unavailable until" in warning for warning in panel.warnings)

    result = await run_backtest(
        session,
        {"A": 0.5, "B": 0.5},
        100.0,
        date(2025, 1, 2),
        date(2025, 1, 6),
        BacktestMode.BUY_AND_HOLD,
    )
    assert result.values == pytest.approx([100.0, 105.0, 115.0])
    assert result.frequency is None
