"""Historical portfolio reconstruction from Phase 2 ``stock_prices`` rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Stock, StockPrice
from app.optimization.types import FloatArray


class BacktestMode(StrEnum):
    BUY_AND_HOLD = "buy_and_hold"
    PERIODIC_REBALANCE = "periodic_rebalance"


class RebalanceFrequency(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


@dataclass(frozen=True, slots=True)
class BacktestPoint:
    trade_date: date
    portfolio_value: float
    portfolio_return: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    mode: BacktestMode
    frequency: RebalanceFrequency | None
    symbols: tuple[str, ...]
    points: tuple[BacktestPoint, ...]
    warnings: tuple[str, ...]

    @property
    def values(self) -> FloatArray:
        return np.asarray([point.portfolio_value for point in self.points], dtype=float)

    @property
    def returns(self) -> FloatArray:
        return np.asarray([point.portfolio_return for point in self.points], dtype=float)


@dataclass(frozen=True, slots=True)
class ReturnPanel:
    dates: tuple[date, ...]
    returns: FloatArray
    observations: FloatArray
    warnings: tuple[str, ...]


def _validate_simulation_inputs(
    returns: FloatArray,
    weights: FloatArray,
    observations: FloatArray | None,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    matrix = np.asarray(returns, dtype=float)
    target = np.asarray(weights, dtype=float)
    present = ~np.isnan(matrix) if observations is None else np.asarray(observations, dtype=bool)
    if matrix.ndim != 2 or target.shape != (matrix.shape[1],):
        raise ValueError("returns must be 2-D and aligned with weights")
    if present.shape != matrix.shape:
        raise ValueError("observations must align with returns")
    if matrix.shape[0] == 0:
        raise ValueError("at least one return date is required")
    if np.any(target < 0) or not np.isclose(np.sum(target), 1.0, atol=1e-8):
        raise ValueError("weights must be non-negative and sum to one")
    return np.nan_to_num(matrix, nan=0.0), target, present


def buy_and_hold_values(
    returns: FloatArray,
    weights: FloatArray,
    budget: float,
    observations: FloatArray | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Simulate drifting asset notionals; unavailable allocations remain cash."""

    matrix, target, present = _validate_simulation_inputs(returns, weights, observations)
    if budget <= 0:
        raise ValueError("budget in INR must be positive")
    allocations = np.zeros(target.size, dtype=float)
    first_available = present[0]
    allocations[first_available] = budget * target[first_available]
    cash = float(budget - np.sum(allocations))
    ever_available = first_available.copy()
    values = np.empty(matrix.shape[0], dtype=float)
    periodic_returns = np.zeros(matrix.shape[0], dtype=float)
    values[0] = budget
    for row_index in range(1, matrix.shape[0]):
        newly_available = present[row_index] & ~ever_available
        initial_allocations = budget * target[newly_available]
        allocations[newly_available] = initial_allocations
        cash -= float(np.sum(initial_allocations))
        ever_available |= present[row_index]
        allocations *= 1.0 + matrix[row_index]
        values[row_index] = cash + float(np.sum(allocations))
        periodic_returns[row_index] = values[row_index] / values[row_index - 1] - 1.0
    return values, periodic_returns


def rebalance_schedule(
    dates: tuple[date, ...], frequency: RebalanceFrequency
) -> FloatArray:
    """Return a Boolean mask marking the first observation in each new period."""

    mask = np.zeros(len(dates), dtype=bool)
    for index in range(1, len(dates)):
        previous, current = dates[index - 1], dates[index]
        if frequency is RebalanceFrequency.WEEKLY:
            changed = previous.isocalendar()[:2] != current.isocalendar()[:2]
        elif frequency is RebalanceFrequency.MONTHLY:
            changed = (previous.year, previous.month) != (current.year, current.month)
        elif frequency is RebalanceFrequency.QUARTERLY:
            changed = (previous.year, (previous.month - 1) // 3) != (
                current.year,
                (current.month - 1) // 3,
            )
        else:
            changed = previous.year != current.year
        mask[index] = changed
    return mask


def periodic_rebalance_values(
    returns: FloatArray,
    weights: FloatArray,
    budget: float,
    rebalance_mask: FloatArray,
    observations: FloatArray | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Simulate target-weight resets on dates selected by ``rebalance_mask``."""

    matrix, target, present = _validate_simulation_inputs(returns, weights, observations)
    schedule = np.asarray(rebalance_mask, dtype=bool)
    if schedule.shape != (matrix.shape[0],):
        raise ValueError("rebalance_mask must have one entry per return row")
    if budget <= 0:
        raise ValueError("budget in INR must be positive")
    listed = present[0].copy()
    allocations = budget * target * listed
    cash = float(budget - np.sum(allocations))
    values = np.empty(matrix.shape[0], dtype=float)
    periodic_returns = np.zeros(matrix.shape[0], dtype=float)
    values[0] = budget
    for row_index in range(1, matrix.shape[0]):
        listed |= present[row_index]
        previous_value = values[row_index - 1]
        if schedule[row_index]:
            allocations = previous_value * target * listed
            cash = float(previous_value - np.sum(allocations))
        allocations *= 1.0 + matrix[row_index]
        values[row_index] = cash + float(np.sum(allocations))
        periodic_returns[row_index] = values[row_index] / previous_value - 1.0
    return values, periodic_returns


async def fetch_return_panel(
    session: AsyncSession,
    symbols: tuple[str, ...],
    start_date: date,
    end_date: date,
) -> ReturnPanel:
    """Query real dated rows and align them without inventing market dates.

    The 47 zero-OHLC source rows rejected during ETL are naturally absent here;
    when peer holdings establish that date, the missing position receives 0% return.
    """

    if not symbols or len(set(symbols)) != len(symbols):
        raise ValueError("symbols must be a non-empty unique tuple")
    if end_date < start_date:
        raise ValueError("end_date must not precede start_date")
    rows = (
        await session.execute(
            select(Stock.symbol, StockPrice.trade_date, StockPrice.daily_return)
            .join(StockPrice, StockPrice.stock_id == Stock.id)
            .where(
                Stock.symbol.in_(symbols),
                StockPrice.trade_date >= start_date,
                StockPrice.trade_date <= end_date,
            )
            .order_by(StockPrice.trade_date, Stock.symbol)
        )
    ).all()
    if not rows:
        raise ValueError("no stock_prices rows exist for the requested universe and range")
    dates = tuple(sorted({trade_date for _, trade_date, _ in rows}))
    date_index = {trade_date: index for index, trade_date in enumerate(dates)}
    symbol_index = {symbol: index for index, symbol in enumerate(symbols)}
    matrix = np.full((len(dates), len(symbols)), np.nan, dtype=float)
    observations = np.zeros_like(matrix, dtype=bool)
    for symbol, trade_date, daily_return in rows:
        column = symbol_index[symbol]
        row = date_index[trade_date]
        observations[row, column] = True
        matrix[row, column] = 0.0 if daily_return is None else float(daily_return)

    warnings: list[str] = []
    for column, symbol in enumerate(symbols):
        observed_indices = np.flatnonzero(observations[:, column])
        if observed_indices.size == 0:
            warnings.append(f"{symbol}: no rows in range; target allocation remained cash")
            continue
        first = int(observed_indices[0])
        if first > 0:
            warnings.append(
                f"{symbol}: unavailable until {dates[first].isoformat()}; allocation remained cash"
            )
        gap_count = int(np.count_nonzero(~observations[first:, column]))
        if gap_count:
            warnings.append(
                f"{symbol}: {gap_count} missing trading observations treated as 0% return"
            )
    return ReturnPanel(dates, matrix, observations, tuple(warnings))


async def run_backtest(
    session: AsyncSession,
    weights: dict[str, float],
    budget: float,
    start_date: date,
    end_date: date,
    mode: BacktestMode = BacktestMode.PERIODIC_REBALANCE,
    frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY,
) -> BacktestResult:
    """Run a database-backed historical reconstruction for FR-7."""

    symbols = tuple(weights)
    target = np.asarray([weights[symbol] for symbol in symbols], dtype=float)
    panel = await fetch_return_panel(session, symbols, start_date, end_date)
    if mode is BacktestMode.BUY_AND_HOLD:
        values, returns = buy_and_hold_values(
            panel.returns, target, budget, panel.observations
        )
        selected_frequency = None
    else:
        values, returns = periodic_rebalance_values(
            panel.returns,
            target,
            budget,
            rebalance_schedule(panel.dates, frequency),
            panel.observations,
        )
        selected_frequency = frequency
    points = tuple(
        BacktestPoint(trade_date, float(value), float(periodic_return))
        for trade_date, value, periodic_return in zip(
            panel.dates, values, returns, strict=True
        )
    )
    return BacktestResult(mode, selected_frequency, symbols, points, panel.warnings)
