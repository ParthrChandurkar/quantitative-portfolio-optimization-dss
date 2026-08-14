"""Owned-snapshot adapter for the Phase 7 analytics service."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import (
    AnalyticsDateRange,
    SnapshotAnalyticsInput,
    get_analytics,
)
from app.core.config import Settings
from app.db.models import ConstraintLog, OptimizationRun, PortfolioHolding, Stock, User
from app.optimization.types import ConstraintReport
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


async def constraint_reports(
    session: AsyncSession, run_id: uuid.UUID
) -> tuple[ConstraintReport, ...]:
    rows = (
        await session.scalars(
            select(ConstraintLog).where(ConstraintLog.optimization_run_id == run_id)
        )
    ).all()
    return tuple(
        ConstraintReport(
            row.constraint_name,
            True,
            row.is_binding,
            float(row.slack_value) if row.slack_value is not None else None,
            float(row.shadow_price) if row.shadow_price is not None else None,
        )
        for row in rows
    )


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
) -> dict:
    snapshot = await require_owned_snapshot(
        session, portfolio_id, snapshot_id, user.id
    )
    run = await session.get(OptimizationRun, snapshot.optimization_run_id)
    if run is None:
        raise ValueError("snapshot optimization run is missing")
    symbols, weights = await snapshot_holdings(session, snapshot.id)
    context = await problem_from_run(session, settings, run, symbols)
    selected_end = end_date or context.as_of_date
    selected_start = start_date or selected_end - timedelta(days=365)
    bundle = await get_analytics(
        SnapshotAnalyticsInput(
            weights, await constraint_reports(session, snapshot.optimization_run_id)
        ),
        context.problem,
        AnalyticsDateRange(selected_start, selected_end),
        session=session,
        horizon_years=horizon_years,
    )
    return jsonable_encoder(bundle)
