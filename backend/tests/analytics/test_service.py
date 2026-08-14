from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import (
    AnalyticsDateRange,
    SnapshotAnalyticsInput,
    get_analytics,
)
from app.db.models import Sector, Stock, StockPrice
from app.optimization.types import ConstraintReport, OptimizationInput


async def test_service_returns_chart_ready_complete_bundle(
    session: AsyncSession,
    analytics_universe: OptimizationInput,
) -> None:
    sectors: dict[str, Sector] = {}
    stocks: list[Stock] = []
    for symbol, sector_name in zip(
        analytics_universe.symbols, analytics_universe.sectors, strict=True
    ):
        sector = sectors.setdefault(sector_name, Sector(name=sector_name))
        stock = Stock(symbol=symbol, company_name=f"{symbol} Ltd", sector=sector)
        stocks.append(stock)
        session.add(stock)
    await session.flush()
    start = date(2025, 1, 2)
    for stock_index, stock in enumerate(stocks):
        for day in range(5):
            price = Decimal(100 + stock_index + day)
            session.add(
                StockPrice(
                    stock=stock,
                    trade_date=start + timedelta(days=day),
                    open=price,
                    high=price + 1,
                    low=price - 1,
                    close=price,
                    adj_close=price,
                    volume=1_000,
                    daily_return=None
                    if day == 0
                    else Decimal("0.001") * (stock_index + 1),
                )
            )
    await session.commit()

    snapshot = SnapshotAnalyticsInput(
        weights={symbol: 0.25 for symbol in analytics_universe.symbols},
        constraint_reports=(
            ConstraintReport("C4 Sector cap: Banking", True, False, 0.35),
        ),
    )
    bundle = await get_analytics(
        snapshot,
        analytics_universe,
        AnalyticsDateRange(start, start + timedelta(days=4)),
        session=session,
        horizon_years=3,
        frontier_points=5,
    )

    assert len(bundle.allocation) == 4
    assert sum(row.allocated_amount_inr for row in bundle.allocation) == 100_000.0
    assert len(bundle.growth_projection) == 4
    assert len(bundle.performance.buy_and_hold.points) == 5
    assert len(bundle.performance.periodic_rebalance.points) == 5
    assert np.isfinite(bundle.risk_metrics.realized_annualized_volatility)
    assert len(bundle.efficient_frontier) >= 4
    assert len(bundle.sector_distribution) == 4
