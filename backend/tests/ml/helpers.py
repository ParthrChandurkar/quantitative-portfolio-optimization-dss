from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.db.models import (
    Sector,
    Stock,
    StockFundamental,
    StockPrice,
    StockTechnicalIndicator,
)


async def seed_ml_market(session, observations: int = 100) -> tuple[str, ...]:
    sector = Sector(name=f"ML test {observations}")
    stocks = (
        Stock(symbol="MLAAA", company_name="ML A", sector=sector),
        Stock(symbol="MLBBB", company_name="ML B", sector=sector),
    )
    session.add_all([sector, *stocks])
    await session.flush()
    start = date(2024, 1, 1)
    for stock_index, stock in enumerate(stocks):
        previous = None
        for index in range(observations):
            trade_date = start + timedelta(days=index)
            close = Decimal(str(100 + stock_index * 10 + index * (0.10 + stock_index * 0.02)))
            daily_return = None if previous is None else close / previous - 1
            previous = close
            session.add(
                StockPrice(
                    stock=stock,
                    trade_date=trade_date,
                    open=close,
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    adj_close=close,
                    volume=1_000 + index,
                    daily_return=daily_return,
                )
            )
            session.add(
                StockTechnicalIndicator(
                    stock=stock,
                    trade_date=trade_date,
                    sma_50=close - 1,
                    sma_200=close - 2,
                    rsi_14=Decimal(str(45 + stock_index)),
                    macd=Decimal(str(0.1 + index / 10_000)),
                    volatility_annualized=Decimal("0.20"),
                )
            )
            session.add(
                StockFundamental(
                    stock=stock,
                    as_of_date=trade_date,
                    pe_ratio=Decimal(str(20 + stock_index)),
                    pb_ratio=Decimal(str(3 + stock_index)),
                    market_cap=Decimal(1000000),
                    dividend_yield=Decimal("0.01"),
                    eps=Decimal(10),
                    beta=Decimal(str(0.9 + stock_index * 0.2)),
                )
            )
    await session.commit()
    return tuple(stock.symbol for stock in stocks)
