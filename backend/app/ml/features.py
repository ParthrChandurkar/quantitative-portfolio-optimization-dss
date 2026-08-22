"""Leakage-safe feature construction from the existing PostgreSQL market tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Stock,
    StockFundamental,
    StockPrice,
    StockTechnicalIndicator,
)
from app.optimization.data import TRADING_DAYS

FloatMatrix = NDArray[np.float64]

FEATURE_NAMES: tuple[str, ...] = (
    "return_5d",
    "return_21d",
    "return_63d",
    "price_to_sma50",
    "sma50_to_sma200",
    "rsi_14",
    "macd",
    "realized_volatility_21d",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield",
    "beta",
)
MAX_TRAILING_WINDOW = 63


@dataclass(frozen=True, slots=True)
class FeatureDataset:
    """Plain arrays plus exact dates used for structural leakage assertions."""

    symbols: tuple[str, ...]
    feature_dates: tuple[date, ...]
    values: FloatMatrix
    feature_names: tuple[str, ...] = FEATURE_NAMES
    target_returns: NDArray[np.float64] | None = None
    target_dates: tuple[date, ...] = ()


@dataclass(frozen=True, slots=True)
class _Observation:
    trade_date: date
    adjusted_close: float
    daily_return: float
    sma_50: float
    sma_200: float
    rsi_14: float
    macd: float
    pe_ratio: float
    pb_ratio: float
    dividend_yield: float
    beta: float


def _number(value: object | None) -> float:
    return float(value) if value is not None else float("nan")


def assert_strictly_before(
    feature_dates: tuple[date, ...],
    estimation_end_date: date,
    target_dates: tuple[date, ...] = (),
) -> None:
    """Reject feature or label dates that touch/cross the exclusive cutoff."""

    if not feature_dates:
        raise ValueError("feature dataset is empty")
    if max(feature_dates) >= estimation_end_date:
        raise ValueError("feature dates must be strictly before estimation_end_date")
    if target_dates and max(target_dates) >= estimation_end_date:
        raise ValueError("target dates must be strictly before estimation_end_date")


async def _load_observations(
    session: AsyncSession,
    universe: tuple[str, ...],
    estimation_end_date: date,
) -> dict[str, list[_Observation]]:
    """Follow the optimization data loader's symbol/date query pattern."""

    if not universe:
        raise ValueError("universe must not be empty")
    rows = (
        await session.execute(
            select(
                Stock.symbol,
                StockPrice.trade_date,
                StockPrice.adj_close,
                StockPrice.daily_return,
                StockTechnicalIndicator.sma_50,
                StockTechnicalIndicator.sma_200,
                StockTechnicalIndicator.rsi_14,
                StockTechnicalIndicator.macd,
                StockFundamental.pe_ratio,
                StockFundamental.pb_ratio,
                StockFundamental.dividend_yield,
                StockFundamental.beta,
            )
            .join(StockPrice, StockPrice.stock_id == Stock.id)
            .outerjoin(
                StockTechnicalIndicator,
                and_(
                    StockTechnicalIndicator.stock_id == Stock.id,
                    StockTechnicalIndicator.trade_date == StockPrice.trade_date,
                ),
            )
            .outerjoin(
                StockFundamental,
                and_(
                    StockFundamental.stock_id == Stock.id,
                    StockFundamental.as_of_date == StockPrice.trade_date,
                ),
            )
            .where(
                Stock.symbol.in_(universe),
                StockPrice.trade_date < estimation_end_date,
            )
            .order_by(Stock.symbol, StockPrice.trade_date)
        )
    ).all()
    grouped: dict[str, list[_Observation]] = {symbol: [] for symbol in universe}
    for row in rows:
        grouped[str(row[0])].append(
            _Observation(
                trade_date=row[1],
                adjusted_close=float(row[2]),
                daily_return=_number(row[3]),
                sma_50=_number(row[4]),
                sma_200=_number(row[5]),
                rsi_14=_number(row[6]),
                macd=_number(row[7]),
                pe_ratio=_number(row[8]),
                pb_ratio=_number(row[9]),
                dividend_yield=_number(row[10]),
                beta=_number(row[11]),
            )
        )
    return grouped


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return float("nan")
    return numerator / denominator - 1.0


def _feature_vector(
    observations: list[_Observation],
    closes: FloatMatrix,
    index: int,
) -> list[float]:
    current = observations[index]
    recent_returns = np.asarray(
        [item.daily_return for item in observations[index - 20 : index + 1]],
        dtype=float,
    )
    finite_returns = recent_returns[np.isfinite(recent_returns)]
    realized_volatility = (
        float(np.std(finite_returns, ddof=1) * np.sqrt(TRADING_DAYS))
        if finite_returns.size >= 2
        else float("nan")
    )
    return [
        _safe_ratio(closes[index], closes[index - 5]),
        _safe_ratio(closes[index], closes[index - 21]),
        _safe_ratio(closes[index], closes[index - 63]),
        _safe_ratio(current.adjusted_close, current.sma_50),
        _safe_ratio(current.sma_50, current.sma_200),
        current.rsi_14,
        current.macd,
        realized_volatility,
        current.pe_ratio,
        current.pb_ratio,
        current.dividend_yield,
        current.beta,
    ]


async def build_training_features(
    session: AsyncSession,
    universe: tuple[str, ...],
    estimation_end_date: date,
    *,
    forward_days: int = 21,
    sample_stride: int | None = None,
) -> FeatureDataset:
    """Build trailing features and forward labels entirely before an exclusive cutoff."""

    if forward_days < 1:
        raise ValueError("forward_days must be positive")
    stride = forward_days if sample_stride is None else sample_stride
    if stride < 1:
        raise ValueError("sample_stride must be positive")
    grouped = await _load_observations(session, universe, estimation_end_date)
    symbols: list[str] = []
    feature_dates: list[date] = []
    target_dates: list[date] = []
    values: list[list[float]] = []
    targets: list[float] = []
    for symbol in universe:
        observations = grouped[symbol]
        closes = np.asarray(
            [item.adjusted_close for item in observations], dtype=float
        )
        stop = len(observations) - forward_days
        for index in range(MAX_TRAILING_WINDOW, stop, stride):
            target_index = index + forward_days
            symbols.append(symbol)
            feature_dates.append(observations[index].trade_date)
            target_dates.append(observations[target_index].trade_date)
            values.append(_feature_vector(observations, closes, index))
            targets.append(
                observations[target_index].adjusted_close
                / observations[index].adjusted_close
                - 1.0
            )
    dataset = FeatureDataset(
        tuple(symbols),
        tuple(feature_dates),
        np.asarray(values, dtype=float),
        FEATURE_NAMES,
        np.asarray(targets, dtype=float),
        tuple(target_dates),
    )
    assert_strictly_before(
        dataset.feature_dates, estimation_end_date, dataset.target_dates
    )
    return dataset


async def build_inference_features(
    session: AsyncSession,
    universe: tuple[str, ...],
    as_of_date: date,
) -> FeatureDataset:
    """Return one latest feature row per stock using only dates before ``as_of_date``."""

    grouped = await _load_observations(session, universe, as_of_date)
    feature_dates: list[date] = []
    values: list[list[float]] = []
    for symbol in universe:
        observations = grouped[symbol]
        if len(observations) <= MAX_TRAILING_WINDOW:
            raise ValueError(f"insufficient feature history for {symbol}")
        index = len(observations) - 1
        closes = np.asarray(
            [item.adjusted_close for item in observations], dtype=float
        )
        feature_dates.append(observations[index].trade_date)
        values.append(_feature_vector(observations, closes, index))
    dataset = FeatureDataset(
        universe,
        tuple(feature_dates),
        np.asarray(values, dtype=float),
    )
    assert_strictly_before(dataset.feature_dates, as_of_date)
    return dataset
