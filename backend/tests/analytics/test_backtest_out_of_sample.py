from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.backtest import (
    BacktestMode,
    run_backtest,
    validate_out_of_sample_dates,
)
from app.db.models import Sector, Stock, StockPrice


async def test_fit_and_evaluation_dates_are_structurally_disjoint(
    session: AsyncSession,
) -> None:
    sector = Sector(name="OOS sector")
    first = Stock(symbol="OOSA", company_name="OOS A", sector=sector)
    second = Stock(symbol="OOSB", company_name="OOS B", sector=sector)
    session.add_all([sector, first, second])
    await session.flush()
    dates = tuple(date(2025, 1, day) for day in range(2, 10))
    for stock in (first, second):
        for index, trade_date in enumerate(dates):
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
                    daily_return=None if index == 0 else Decimal("0.001"),
                )
            )
    await session.commit()

    split = date(2025, 1, 6)
    fit_dates = dates[:4]
    result = await run_backtest(
        session,
        {"OOSA": 0.5, "OOSB": 0.5},
        100_000,
        dates[0],
        dates[-1],
        BacktestMode.PERIODIC_REBALANCE,
        estimation_end_date=split,
        estimation_dates=fit_dates,
    )
    evaluation_dates = tuple(point.trade_date for point in result.points)

    assert max(fit_dates) < split <= min(evaluation_dates)
    assert set(fit_dates).isdisjoint(evaluation_dates)
    assert result.validation_mode == "out_of_sample"
    assert result.estimation_end_date == split


def test_overlap_cannot_be_bypassed_by_plausible_numeric_results() -> None:
    split = date(2025, 1, 6)
    with pytest.raises(ValueError, match="strictly before"):
        validate_out_of_sample_dates(
            (date(2025, 1, 5), split),
            (split, date(2025, 1, 7)),
            split,
        )
