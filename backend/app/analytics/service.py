"""Public chart-ready aggregator for the Phase 7 Analytics Dashboard."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.backtest import (
    BacktestMode,
    BacktestResult,
    RebalanceFrequency,
    run_backtest,
)
from app.analytics.efficient_frontier import FrontierPoint, build_efficient_frontier
from app.analytics.growth_projection import (
    GrowthPoint,
    portfolio_moments,
    project_growth,
)
from app.analytics.risk_metrics import RiskMetrics, build_risk_metrics
from app.analytics.sector_distribution import (
    SectorAllocation,
    aggregate_sector_distribution,
)
from app.optimization.types import ConstraintReport, OptimizationInput


@dataclass(frozen=True, slots=True)
class AnalyticsDateRange:
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")


@dataclass(frozen=True, slots=True)
class SnapshotAnalyticsInput:
    weights: Mapping[str, float]
    constraint_reports: tuple[ConstraintReport, ...] = ()


@dataclass(frozen=True, slots=True)
class AllocationPoint:
    symbol: str
    sector: str
    weight: float
    allocated_amount_inr: float


@dataclass(frozen=True, slots=True)
class RiskReturnPoint:
    expected_return: float
    volatility: float


@dataclass(frozen=True, slots=True)
class PerformanceAnalytics:
    buy_and_hold: BacktestResult
    periodic_rebalance: BacktestResult


@dataclass(frozen=True, slots=True)
class AnalyticsBundle:
    allocation: tuple[AllocationPoint, ...]
    risk_return: RiskReturnPoint
    growth_projection: tuple[GrowthPoint, ...]
    performance: PerformanceAnalytics
    risk_metrics: RiskMetrics
    efficient_frontier: tuple[FrontierPoint, ...]
    sector_distribution: tuple[SectorAllocation, ...]


def _normalize_snapshot(
    snapshot_or_weights: SnapshotAnalyticsInput | Mapping[str, float],
) -> SnapshotAnalyticsInput:
    if isinstance(snapshot_or_weights, SnapshotAnalyticsInput):
        return snapshot_or_weights
    return SnapshotAnalyticsInput(snapshot_or_weights)


async def get_analytics(
    snapshot_or_weights: SnapshotAnalyticsInput | Mapping[str, float],
    universe: OptimizationInput,
    date_range: AnalyticsDateRange | tuple[date, date],
    *,
    session: AsyncSession,
    horizon_years: int = 10,
    frontier_points: int = 30,
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY,
) -> AnalyticsBundle:
    """Compute every Analytics Dashboard tab from one consistent input bundle."""

    snapshot = _normalize_snapshot(snapshot_or_weights)
    selected_range = (
        date_range
        if isinstance(date_range, AnalyticsDateRange)
        else AnalyticsDateRange(*date_range)
    )
    unknown = set(snapshot.weights) - set(universe.symbols)
    if unknown:
        raise ValueError(f"weights contain symbols outside universe: {sorted(unknown)}")
    weights = np.asarray(
        [float(snapshot.weights.get(symbol, 0.0)) for symbol in universe.symbols],
        dtype=float,
    )
    if np.any(weights < 0) or not np.isclose(np.sum(weights), 1.0, atol=1e-8):
        raise ValueError("snapshot weights must be non-negative and sum to one")
    weight_map = dict(zip(universe.symbols, weights.tolist(), strict=True))

    buy_and_hold = await run_backtest(
        session,
        weight_map,
        universe.budget,
        selected_range.start_date,
        selected_range.end_date,
        BacktestMode.BUY_AND_HOLD,
    )
    periodic = await run_backtest(
        session,
        weight_map,
        universe.budget,
        selected_range.start_date,
        selected_range.end_date,
        BacktestMode.PERIODIC_REBALANCE,
        rebalance_frequency,
    )
    if len(periodic.points) < 2:
        raise ValueError("analytics requires at least two market dates")

    expected_return, volatility = portfolio_moments(
        weights, universe.expected_returns, universe.covariance
    )
    allocations = tuple(
        AllocationPoint(
            symbol=symbol,
            sector=sector,
            weight=float(weight),
            allocated_amount_inr=float(universe.budget * weight),
        )
        for symbol, sector, weight in zip(
            universe.symbols, universe.sectors, weights, strict=True
        )
    )
    return AnalyticsBundle(
        allocation=allocations,
        risk_return=RiskReturnPoint(expected_return, volatility),
        growth_projection=project_growth(
            universe.budget,
            weights,
            universe.expected_returns,
            universe.covariance,
            horizon_years,
        ),
        performance=PerformanceAnalytics(buy_and_hold, periodic),
        risk_metrics=build_risk_metrics(
            universe.budget,
            weights,
            universe.expected_returns,
            universe.covariance,
            universe.risk_free_rate,
            periodic.returns[1:],
            periodic.values,
        ),
        efficient_frontier=build_efficient_frontier(universe, frontier_points),
        sector_distribution=aggregate_sector_distribution(
            weights,
            universe.sectors,
            universe.sector_caps,
            universe.default_sector_cap,
            snapshot.constraint_reports,
        ),
    )
