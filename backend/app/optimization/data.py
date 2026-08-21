"""Build annualized optimization inputs from prices with covariance cache access."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CovarianceCache, Stock, StockPrice
from app.optimization.types import FloatArray

TRADING_DAYS = 252
ReturnEstimationMethod = Literal["historical_mean", "ml_forecast"]


@dataclass(frozen=True, slots=True)
class MarketData:
    symbols: tuple[str, ...]
    expected_returns: FloatArray
    covariance: FloatArray
    historical_returns: FloatArray
    observations: int
    cache_hit: bool
    observation_dates: tuple[date, ...]
    return_estimation_method: ReturnEstimationMethod = "historical_mean"


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


async def _expected_returns_for_method(
    session: AsyncSession,
    symbols: tuple[str, ...],
    as_of_date: date,
    historical_mean: FloatArray,
    return_estimation_method: ReturnEstimationMethod,
    ml_artifact_dir: Path | None,
) -> FloatArray:
    if return_estimation_method == "historical_mean":
        return historical_mean
    if return_estimation_method != "ml_forecast":
        raise ValueError(f"unsupported return_estimation_method: {return_estimation_method}")
    # Local import keeps the OR engine dependency-free; only this data adapter knows ML.
    from app.ml.forecast_service import get_ml_forecast

    # Historical ``as_of_date`` is inclusive. Forecast features are strictly before
    # their timestamp, so the next calendar date represents an after-close forecast
    # while retaining the exact same covariance window as the historical path.
    forecast_date = as_of_date + timedelta(days=1)
    if ml_artifact_dir is None:
        forecast = await get_ml_forecast(session, symbols, forecast_date)
    else:
        forecast = await get_ml_forecast(
            session,
            symbols,
            forecast_date,
            artifact_dir=ml_artifact_dir,
        )
    return forecast.expected_returns


async def build_market_data(
    session: AsyncSession,
    symbols: tuple[str, ...],
    as_of_date: date,
    lookback_days: int = 252,
    return_estimation_method: ReturnEstimationMethod = "historical_mean",
    *,
    ml_artifact_dir: Path | None = None,
) -> MarketData:
    """Read-through/write-through covariance data for FR-2 and FR-4."""

    if len(symbols) < 2:
        raise ValueError("at least two symbols are required")
    if lookback_days < 2:
        raise ValueError("lookback_days must be at least 2")
    if return_estimation_method not in {"historical_mean", "ml_forecast"}:
        raise ValueError(f"unsupported return_estimation_method: {return_estimation_method}")
    digest = universe_hash(symbols)
    cached = await _read_cache(session, digest, lookback_days, as_of_date)
    if (
        cached is not None
        and cached.matrix.get("symbols") == list(symbols)
        and cached.matrix.get("observation_dates")
    ):
        payload = cached.matrix
        history = np.asarray(payload["historical_returns"], dtype=float)
        historical_mean = np.asarray(payload["expected_returns"], dtype=float)
        expected_returns = await _expected_returns_for_method(
            session,
            symbols,
            as_of_date,
            historical_mean,
            return_estimation_method,
            ml_artifact_dir,
        )
        return MarketData(
            symbols,
            expected_returns,
            np.asarray(payload["covariance"], dtype=float),
            history,
            history.shape[0],
            True,
            tuple(date.fromisoformat(value) for value in payload["observation_dates"]),
            return_estimation_method,
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
    historical_mean, covariance = annualize_returns(history)
    await _write_cache(
        session,
        digest,
        lookback_days,
        as_of_date,
        {
            "symbols": list(symbols),
            "expected_returns": historical_mean.tolist(),
            "covariance": covariance.tolist(),
            "historical_returns": history.tolist(),
            "observation_dates": [value.isoformat() for value in observation_dates],
        },
    )
    await session.commit()
    expected_returns = await _expected_returns_for_method(
        session,
        symbols,
        as_of_date,
        historical_mean,
        return_estimation_method,
        ml_artifact_dir,
    )
    return MarketData(
        symbols,
        expected_returns,
        covariance,
        history,
        history.shape[0],
        False,
        observation_dates,
        return_estimation_method,
    )
