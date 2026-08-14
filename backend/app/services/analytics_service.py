"""Owned-snapshot adapter for the Phase 7 analytics service."""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, timedelta

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.backtest import default_out_of_sample_split
from app.analytics.service import (
    AnalyticsDateRange,
    SnapshotAnalyticsInput,
    get_analytics,
)
from app.core.config import Settings
from app.db.models import OptimizationRun, PortfolioHolding, Stock, StockPrice, User
from app.optimization.engine import solve
from app.services.portfolio_service import require_owned_snapshot
from app.services.problem_service import problem_from_run


async def snapshot_holdings(
    session: AsyncSession, snapshot_id: uuid.UUID
) -> tuple[tuple[str, ...], dict[str, float]]:
    rows = (
        await session.execute(
            select(Stock.symbol, PortfolioHolding.weight)
            .join(PortfolioHolding, PortfolioHolding.stock_id == Stock.id)
            .where(PortfolioHolding.snapshot_id == snapshot_id)
            .order_by(Stock.symbol)
        )
    ).all()
    if not rows:
        raise ValueError("snapshot has no holdings")
    return tuple(symbol for symbol, _ in rows), {
        symbol: float(weight) for symbol, weight in rows
    }


async def get_snapshot_analytics(
    session: AsyncSession,
    user: User,
    portfolio_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    settings: Settings,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    horizon_years: int = 10,
    estimation_end_date: date | None = None,
) -> dict:
    snapshot = await require_owned_snapshot(
        session, portfolio_id, snapshot_id, user.id
    )
    run = await session.get(OptimizationRun, snapshot.optimization_run_id)
    if run is None:
        raise ValueError("snapshot optimization run is missing")
    selected_end = end_date or await session.scalar(select(func.max(StockPrice.trade_date)))
    if selected_end is None:
        raise ValueError("analytics requires loaded stock prices")
    split_date = estimation_end_date or await default_out_of_sample_split(
        session, selected_end
    )
    if split_date > selected_end:
        raise ValueError("estimation_end_date must not follow the evaluation end date")
    context = await problem_from_run(
        session,
        settings,
        run,
        None,
        as_of_date=split_date - timedelta(days=1),
    )
    fitted_result = await asyncio.to_thread(solve, context.problem)
    if not fitted_result.is_feasible:
        raise ValueError(
            f"out-of-sample fit optimization failed: {fitted_result.message}"
        )
    selected_start = max(start_date or split_date, split_date)
    bundle = await get_analytics(
        SnapshotAnalyticsInput(
            fitted_result.weights, fitted_result.constraint_reports
        ),
        context.problem,
        AnalyticsDateRange(selected_start, selected_end),
        session=session,
        horizon_years=horizon_years,
        estimation_end_date=split_date,
        estimation_dates=context.estimation_dates,
    )
    return jsonable_encoder(bundle)
