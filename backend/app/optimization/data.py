"""Build annualized optimization inputs from prices with covariance cache access."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CovarianceCache, Stock, StockPrice
from app.optimization.types import FloatArray

TRADING_DAYS = 252


@dataclass(frozen=True, slots=True)
class MarketData:
    symbols: tuple[str, ...]
    expected_returns: FloatArray
    covariance: FloatArray
    historical_returns: FloatArray
    observations: int
    cache_hit: bool
    observation_dates: tuple[date, ...]


def universe_hash(symbols: tuple[str, ...]) -> str:
    canonical = "\n".join(sorted(symbol.upper() for symbol in symbols))
    return hashlib.sha256(canonical.encode()).hexdigest()


def annualize_returns(return_matrix: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Vectorized arithmetic-mean and sample-covariance annualization."""

    if return_matrix.ndim != 2 or return_matrix.shape[0] < 2:
        raise ValueError("at least two aligned return observations are required")
    return (
        np.mean(return_matrix, axis=0) * TRADING_DAYS,
        np.cov(return_matrix, rowvar=False, ddof=1) * TRADING_DAYS,
    )


async def _read_cache(
    session: AsyncSession, digest: str, lookback_days: int, as_of_date: date
) -> CovarianceCache | None:
    return await session.scalar(
        select(CovarianceCache).where(
            CovarianceCache.universe_hash == digest,
            CovarianceCache.lookback_days == lookback_days,
            CovarianceCache.as_of_date == as_of_date,
        )
    )


async def _write_cache(
    session: AsyncSession,
    digest: str,
    lookback_days: int,
    as_of_date: date,
    matrix: dict[str, Any],
) -> None:
    values = {
        "universe_hash": digest,
        "lookback_days": lookback_days,
        "as_of_date": as_of_date,
        "matrix": matrix,
    }
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        statement: Any = postgresql_insert(CovarianceCache).values(**values)
    elif dialect == "sqlite":
        statement = sqlite_insert(CovarianceCache).values(**values)
    else:
        raise RuntimeError(f"covariance caching is unsupported for {dialect!r}")
    statement = statement.on_conflict_do_update(
        index_elements=[
            CovarianceCache.universe_hash,
            CovarianceCache.lookback_days,
            CovarianceCache.as_of_date,
        ],
        set_={"matrix": matrix},
    )
    await session.execute(statement)


async def build_market_data(
    session: AsyncSession,
    symbols: tuple[str, ...],
    as_of_date: date,
    lookback_days: int = 252,
) -> MarketData:
    """Read-through/write-through covariance data for FR-2 and FR-4."""

    if len(symbols) < 2:
        raise ValueError("at least two symbols are required")
    if lookback_days < 2:
        raise ValueError("lookback_days must be at least 2")
    digest = universe_hash(symbols)
    cached = await _read_cache(session, digest, lookback_days, as_of_date)
    if (
        cached is not None
        and cached.matrix.get("symbols") == list(symbols)
        and cached.matrix.get("observation_dates")
    ):
        payload = cached.matrix
        history = np.asarray(payload["historical_returns"], dtype=float)
        return MarketData(
            symbols,
            np.asarray(payload["expected_returns"], dtype=float),
            np.asarray(payload["covariance"], dtype=float),
            history,
            history.shape[0],
            True,
            tuple(date.fromisoformat(value) for value in payload["observation_dates"]),
        )

    rows = (
        await session.execute(
            select(Stock.symbol, StockPrice.trade_date, StockPrice.daily_return)
            .join(StockPrice, StockPrice.stock_id == Stock.id)
            .where(
                Stock.symbol.in_(symbols),
                StockPrice.trade_date <= as_of_date,
                StockPrice.daily_return.is_not(None),
            )
            .order_by(StockPrice.trade_date.desc())
        )
    ).all()
    by_date: dict[date, dict[str, float]] = {}
    for symbol, trade_date, daily_return in rows:
        by_date.setdefault(trade_date, {})[symbol] = float(daily_return)
    aligned_rows = [
        (trade_date, [values[symbol] for symbol in symbols])
        for trade_date, values in sorted(by_date.items(), reverse=True)
        if all(symbol in values for symbol in symbols)
    ][:lookback_days]
    aligned_rows.reverse()
    observation_dates = tuple(trade_date for trade_date, _ in aligned_rows)
    aligned = [values for _, values in aligned_rows]
    history = np.asarray(aligned, dtype=float)
    expected_returns, covariance = annualize_returns(history)
    await _write_cache(
        session,
        digest,
        lookback_days,
        as_of_date,
        {
            "symbols": list(symbols),
            "expected_returns": expected_returns.tolist(),
            "covariance": covariance.tolist(),
            "historical_returns": history.tolist(),
            "observation_dates": [value.isoformat() for value in observation_dates],
        },
    )
    await session.commit()
    return MarketData(
        symbols,
        expected_returns,
        covariance,
        history,
        history.shape[0],
        False,
        observation_dates,
    )
