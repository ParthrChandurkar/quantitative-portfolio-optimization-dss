"""Chronological walk-forward estimation, optimization, and realized simulation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.backtest import (
    RebalanceFrequency,
    compound_rebalance_period,
    fetch_return_panel,
    rebalance_schedule,
)
from app.core.config import Settings
from app.db.models import OptimizationRun
from app.optimization.engine import solve
from app.optimization.types import FloatArray
from app.services.problem_service import (
    ProblemContext,
    problem_from_run,
    stock_universe,
)


@dataclass(frozen=True, slots=True)
class WalkForwardPoint:
    trade_date: date
    portfolio_value: float
    portfolio_return: float


@dataclass(frozen=True, slots=True)
class WalkForwardPeriod:
    period_number: int
    rebalance_date: date
    holding_end_date: date
    estimation_start_date: date
    estimation_end_date: date
    estimation_observations: int
    weights: dict[str, float]
    turnover: float
    expected_return: float
    expected_volatility: float


@dataclass(frozen=True, slots=True)
class WalkForwardSimulation:
    symbols: tuple[str, ...]
    frequency: RebalanceFrequency
    lookback_days: int
    points: tuple[WalkForwardPoint, ...]
    periods: tuple[WalkForwardPeriod, ...]
    total_turnover: float
    warnings: tuple[str, ...]

    @property
    def values(self) -> FloatArray:
        return np.asarray([point.portfolio_value for point in self.points], dtype=float)

    @property
    def returns(self) -> FloatArray:
        return np.asarray(
            [point.portfolio_return for point in self.points], dtype=float
        )


@dataclass(frozen=True, slots=True)
class RebalanceDecision:
    context: ProblemContext
    weights: dict[str, float]
    turnover: float
    expected_return: float
    expected_volatility: float


def assert_pre_rebalance_estimation(
    estimation_dates: tuple[date, ...], rebalance_date: date
) -> None:
    """Reject any period whose fit data reaches or crosses its decision date."""

    if not estimation_dates:
        raise ValueError("walk-forward estimation requires dated observations")
    invalid = tuple(value for value in estimation_dates if value >= rebalance_date)
    if invalid:
        raise ValueError(
            "walk-forward look-ahead detected: every estimation date must be "
            f"strictly before {rebalance_date.isoformat()}"
        )


def walk_forward_rebalance_dates(
    market_dates: tuple[date, ...], frequency: RebalanceFrequency
) -> tuple[date, ...]:
    """Select the first tradable date and each later period boundary."""

    if not market_dates:
        raise ValueError("walk-forward requires at least one market date")
    mask = rebalance_schedule(market_dates, frequency)
    return (market_dates[0],) + tuple(
        value for value, selected in zip(market_dates, mask, strict=True) if selected
    )


async def optimize_rebalance_period(
    session: AsyncSession,
    settings: Settings,
    run: OptimizationRun,
    symbols: tuple[str, ...],
    rebalance_date: date,
    lookback_days: int,
    previous_weights: dict[str, float] | None = None,
) -> RebalanceDecision:
    """Estimate and solve one independently testable walk-forward period."""

    context = await problem_from_run(
        session,
        settings,
        run,
        symbols,
        as_of_date=rebalance_date - timedelta(days=1),
        lookback_days=lookback_days,
    )
    assert_pre_rebalance_estimation(context.estimation_dates, rebalance_date)
    result = await asyncio.to_thread(solve, context.problem)
    if not result.is_feasible:
        raise ValueError(
            f"walk-forward solve failed on {rebalance_date.isoformat()}: {result.message}"
        )
    weights = {symbol: float(result.weights.get(symbol, 0.0)) for symbol in symbols}
    previous = previous_weights or weights
    turnover = float(
        sum(abs(weights[symbol] - previous.get(symbol, 0.0)) for symbol in symbols)
    )
    if result.expected_return is None or result.expected_volatility is None:
        raise ValueError("walk-forward solver omitted portfolio metrics")
    return RebalanceDecision(
        context,
        weights,
        0.0 if previous_weights is None else turnover,
        float(result.expected_return),
        float(result.expected_volatility),
    )


async def run_walk_forward_simulation(
    session: AsyncSession,
    settings: Settings,
    run: OptimizationRun,
    start_date: date,
    end_date: date,
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY,
    lookback_days: int = 252,
) -> WalkForwardSimulation:
    """Re-estimate, re-optimize, and hold over successive real market periods."""

    if end_date < start_date:
        raise ValueError("end_date must not precede start_date")
    if lookback_days < 2:
        raise ValueError("lookback_days must be at least 2")
    stocks, _ = await stock_universe(session)
    symbols = tuple(stock.symbol for stock in stocks)
    panel = await fetch_return_panel(session, symbols, start_date, end_date)
    rebalance_dates = walk_forward_rebalance_dates(panel.dates, rebalance_frequency)
    date_index = {value: index for index, value in enumerate(panel.dates)}

    points: list[WalkForwardPoint] = []
    periods: list[WalkForwardPeriod] = []
    previous_weights: dict[str, float] | None = None
    current_value = float(run.budget)
    # Transaction costs are intentionally omitted; precise turnover is exposed instead.
    for period_number, rebalance_date in enumerate(rebalance_dates, start=1):
        decision = await optimize_rebalance_period(
            session,
            settings,
            run,
            symbols,
            rebalance_date,
            lookback_days,
            previous_weights,
        )
        assert_pre_rebalance_estimation(
            decision.context.estimation_dates, rebalance_date
        )
        start_index = date_index[rebalance_date]
        end_index = (
            date_index[rebalance_dates[period_number]]
            if period_number < len(rebalance_dates)
            else len(panel.dates)
        )
        segment_returns = panel.returns[start_index:end_index]
        segment_observations = panel.observations[start_index:end_index]
        if period_number == 1:
            # Match the Phase 9C convention: the first evaluation point establishes
            # the opening value and therefore has a zero portfolio return.
            segment_returns = segment_returns.copy()
            segment_returns[0] = 0.0
        weight_vector = np.asarray(
            [decision.weights[symbol] for symbol in symbols], dtype=float
        )
        values, returns = compound_rebalance_period(
            segment_returns,
            weight_vector,
            current_value,
            segment_observations,
        )
        segment_dates = panel.dates[start_index:end_index]
        points.extend(
            WalkForwardPoint(day, float(value), float(period_return))
            for day, value, period_return in zip(
                segment_dates, values, returns, strict=True
            )
        )
        current_value = float(values[-1])
        periods.append(
            WalkForwardPeriod(
                period_number,
                rebalance_date,
                segment_dates[-1],
                decision.context.estimation_dates[0],
                decision.context.estimation_dates[-1],
                len(decision.context.estimation_dates),
                decision.weights,
                decision.turnover,
                decision.expected_return,
                decision.expected_volatility,
            )
        )
        previous_weights = decision.weights
    return WalkForwardSimulation(
        symbols,
        rebalance_frequency,
        lookback_days,
        tuple(points),
        tuple(periods),
        float(sum(period.turnover for period in periods)),
        panel.warnings,
    )
