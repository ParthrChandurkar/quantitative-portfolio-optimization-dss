"""Persist and deduplicate personalized alerts for owned portfolios."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.alerts.risk_drift_detector import detect_risk_drift
from app.alerts.stock_anomaly_detector import detect_stock_anomalies
from app.alerts.types import Alert
from app.core.errors import APIError
from app.db.models import (
    Alert as StoredAlert,
)
from app.db.models import (
    Portfolio,
    PortfolioHolding,
    PortfolioSnapshot,
    Stock,
    StockPrice,
    UserRiskProfile,
)

logger = logging.getLogger(__name__)


async def check_alerts_in_background(
    engine: AsyncEngine,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID,
) -> None:
    """Run a post-response alert check in its own database session."""

    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        try:
            await check_alerts(session, user_id, portfolio_id)
        except Exception:
            await session.rollback()
            logger.exception(
                "Background alert check failed for user=%s portfolio=%s",
                user_id,
                portfolio_id,
            )


async def _latest_profile(
    session: AsyncSession, user_id: uuid.UUID
) -> UserRiskProfile | None:
    return await session.scalar(
        select(UserRiskProfile)
        .where(UserRiskProfile.user_id == user_id)
        .order_by(UserRiskProfile.created_at.desc(), UserRiskProfile.id.desc())
        .limit(1)
    )


async def _snapshot_context(
    session: AsyncSession, portfolio_id: uuid.UUID
) -> tuple[PortfolioSnapshot | None, int]:
    snapshot_count = await session.scalar(
        select(func.count(PortfolioSnapshot.id)).where(
            PortfolioSnapshot.portfolio_id == portfolio_id
        )
    )
    latest = await session.scalar(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.created_at.desc(), PortfolioSnapshot.id.desc())
        .limit(1)
    )
    return latest, int(snapshot_count or 0)


async def _held_stocks(
    session: AsyncSession, snapshot_id: uuid.UUID
) -> tuple[tuple[uuid.UUID, str], ...]:
    rows = (
        await session.execute(
            select(Stock.id, Stock.symbol)
            .join(PortfolioHolding, PortfolioHolding.stock_id == Stock.id)
            .where(PortfolioHolding.snapshot_id == snapshot_id)
            .order_by(Stock.symbol)
        )
    ).all()
    return tuple((row[0], str(row[1])) for row in rows)


def _condition_key(
    alert_type: str, stock_id: uuid.UUID | None
) -> tuple[str, str | None]:
    return alert_type, str(stock_id) if stock_id is not None else None


async def check_alerts(
    session: AsyncSession,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID,
) -> list[StoredAlert]:
    portfolio = await session.scalar(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if portfolio is None:
        raise APIError(403, "PORTFOLIO_FORBIDDEN", "You do not own this portfolio")
    if not portfolio.is_active:
        return []

    snapshot, snapshot_count = await _snapshot_context(session, portfolio_id)
    # A single optimized snapshot is a baseline, not drift. All alert families wait
    # for a later snapshot so first-time users never receive immediate warnings.
    if snapshot is None or snapshot_count < 2:
        return []
    profile = await _latest_profile(session, user_id)
    if profile is None:
        return []

    candidates: list[Alert] = detect_risk_drift(snapshot, profile)
    holdings = await _held_stocks(session, snapshot.id)
    if holdings:
        latest_date = await session.scalar(
            select(func.max(StockPrice.trade_date)).where(
                StockPrice.stock_id.in_(tuple(stock_id for stock_id, _ in holdings))
            )
        )
        if latest_date is not None:
            candidates.extend(
                await detect_stock_anomalies(
                    session,
                    holdings,
                    latest_date + timedelta(days=1),
                    snapshot.id,
                )
            )

    existing = (
        await session.scalars(
            select(StoredAlert).where(
                StoredAlert.user_id == user_id,
                StoredAlert.portfolio_id == portfolio_id,
                StoredAlert.acknowledged.is_(False),
            )
        )
    ).all()
    by_condition = {
        _condition_key(row.alert_type, row.stock_id): row for row in existing
    }
    active: list[StoredAlert] = []
    for candidate in candidates:
        key = _condition_key(candidate.alert_type.value, candidate.stock_id)
        if key in by_condition:
            active.append(by_condition[key])
            continue
        row = StoredAlert(
            user_id=user_id,
            portfolio_id=portfolio_id,
            snapshot_id=candidate.snapshot_id,
            stock_id=candidate.stock_id,
            alert_type=candidate.alert_type.value,
            severity=candidate.severity.value,
            message=candidate.message,
            grounding=candidate.grounding,
        )
        session.add(row)
        active.append(row)
    if candidates:
        await session.commit()
    return active
