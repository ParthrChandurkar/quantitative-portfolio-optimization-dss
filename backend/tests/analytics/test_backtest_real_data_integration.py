from __future__ import annotations

import os
from datetime import date
from itertools import pairwise

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.analytics.backtest import BacktestMode, run_backtest

REAL_DATABASE_URL = os.getenv("REAL_DATABASE_URL")


@pytest.mark.skipif(
    not REAL_DATABASE_URL,
    reason="set REAL_DATABASE_URL to run against the loaded Nifty-50 PostgreSQL database",
)
async def test_one_year_five_stock_backtest_uses_real_postgres_data() -> None:
    assert REAL_DATABASE_URL is not None
    engine = create_async_engine(REAL_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    weights = {
        "RELIANCE": 0.20,
        "TCS": 0.20,
        "HDFCBANK": 0.20,
        "INFY": 0.20,
        "ITC": 0.20,
    }
    try:
        async with factory() as session:
            result = await run_backtest(
                session,
                weights,
                1_000_000.0,
                date(2025, 1, 1),
                date(2025, 12, 31),
                BacktestMode.PERIODIC_REBALANCE,
            )
    finally:
        await engine.dispose()

    dates = [point.trade_date for point in result.points]
    assert len(dates) >= 240
    assert dates == sorted(set(dates))
    assert max((current - previous).days for previous, current in pairwise(dates)) <= 7
    assert np.isfinite(result.points[-1].portfolio_value)
    assert result.points[-1].portfolio_value > 0
