from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pytest
from sqlalchemy import func, select

from app.db.models import CovarianceCache, Sector, Stock, StockPrice
from app.optimization.data import annualize_returns, build_market_data, universe_hash


async def test_covariance_cache_read_through_and_write_through(session) -> None:
    sector = Sector(name="Test")
    first = Stock(symbol="AAA", company_name="AAA", sector=sector)
    second = Stock(symbol="BBB", company_name="BBB", sector=sector)
    session.add_all([first, second])
    await session.flush()
    start = date(2026, 1, 1)
    for day in range(5):
        for stock, daily_return in ((first, 0.01 + day * 0.001), (second, 0.02 - day * 0.001)):
            close = Decimal(100) + day
            session.add(
                StockPrice(
                    stock_id=stock.id,
                    trade_date=start + timedelta(days=day),
                    open=close,
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    adj_close=close,
                    volume=1000,
                    daily_return=Decimal(str(daily_return)),
                )
            )
    await session.commit()
    generated = await build_market_data(session, ("AAA", "BBB"), start + timedelta(days=4), 4)
    cached = await build_market_data(session, ("AAA", "BBB"), start + timedelta(days=4), 4)
    assert generated.cache_hit is False
    assert cached.cache_hit is True
    assert generated.observations == 4
    assert np.allclose(generated.covariance, cached.covariance)
    assert await session.scalar(select(func.count()).select_from(CovarianceCache)) == 1
    assert len(universe_hash(("AAA", "BBB"))) == 64


def test_annualization_validates_observation_count() -> None:
    with pytest.raises(ValueError, match="at least two"):
        annualize_returns(np.ones((1, 2)))


async def test_market_data_validates_inputs(session) -> None:
    with pytest.raises(ValueError, match="at least two symbols"):
        await build_market_data(session, ("AAA",), date(2026, 1, 1))
    with pytest.raises(ValueError, match="lookback_days"):
        await build_market_data(session, ("AAA", "BBB"), date(2026, 1, 1), 1)
