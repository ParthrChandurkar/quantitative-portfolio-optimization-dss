"""User-owned portfolio and snapshot persistence operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.db.models import Portfolio, PortfolioSnapshot, User
from app.schemas.portfolios import PortfolioCreateRequest, PortfolioUpdateRequest


def snapshot_payload(snapshot: PortfolioSnapshot) -> dict:
    return {
        "id": snapshot.id,
        "label": snapshot.label,
        "expected_return": float(snapshot.expected_return)
        if snapshot.expected_return is not None
        else None,
        "expected_volatility": float(snapshot.expected_volatility)
        if snapshot.expected_volatility is not None
        else None,
        "sharpe_ratio": float(snapshot.sharpe_ratio)
        if snapshot.sharpe_ratio is not None
        else None,
        "diversification_score": float(snapshot.diversification_score)
        if snapshot.diversification_score is not None
        else None,
        "is_baseline": snapshot.is_baseline,
        "created_at": snapshot.created_at,
    }


async def require_owned_portfolio(
    session: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID
) -> Portfolio:
    portfolio = await session.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != user_id:
        raise APIError(403, "PORTFOLIO_FORBIDDEN", "You do not own this portfolio")
    return portfolio


async def require_owned_snapshot(
    session: AsyncSession,
    portfolio_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PortfolioSnapshot:
    await require_owned_portfolio(session, portfolio_id, user_id)
    snapshot = await session.get(PortfolioSnapshot, snapshot_id)
    if snapshot is None or snapshot.portfolio_id != portfolio_id:
        raise APIError(403, "SNAPSHOT_FORBIDDEN", "You do not own this snapshot")
    return snapshot


async def list_portfolios(session: AsyncSession, user: User) -> list[dict]:
    portfolios = (
        await session.scalars(
            select(Portfolio)
            .where(Portfolio.user_id == user.id)
            .order_by(Portfolio.created_at.desc())
        )
    ).all()
    return [await portfolio_payload(session, portfolio) for portfolio in portfolios]


async def latest_snapshot(
    session: AsyncSession, portfolio_id: uuid.UUID
) -> PortfolioSnapshot | None:
    return await session.scalar(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.created_at.desc())
        .limit(1)
    )


async def portfolio_payload(session: AsyncSession, portfolio: Portfolio) -> dict:
    snapshot = await latest_snapshot(session, portfolio.id)
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "is_active": portfolio.is_active,
        "created_at": portfolio.created_at,
        "latest_snapshot": snapshot_payload(snapshot) if snapshot is not None else None,
    }


async def create_portfolio(
    session: AsyncSession, user: User, request: PortfolioCreateRequest
) -> dict:
    portfolio = Portfolio(user_id=user.id, name=request.name.strip(), is_active=True)
    session.add(portfolio)
    await session.commit()
    await session.refresh(portfolio)
    return await portfolio_payload(session, portfolio)


async def get_portfolio(
    session: AsyncSession, user: User, portfolio_id: uuid.UUID
) -> dict:
    portfolio = await require_owned_portfolio(session, portfolio_id, user.id)
    return await portfolio_payload(session, portfolio)


async def update_portfolio(
    session: AsyncSession,
    user: User,
    portfolio_id: uuid.UUID,
    request: PortfolioUpdateRequest,
) -> dict:
    portfolio = await require_owned_portfolio(session, portfolio_id, user.id)
    if request.name is not None:
        portfolio.name = request.name.strip()
    if request.is_active is not None:
        portfolio.is_active = request.is_active
    await session.commit()
    await session.refresh(portfolio)
    return await portfolio_payload(session, portfolio)


async def list_snapshots(
    session: AsyncSession, user: User, portfolio_id: uuid.UUID
) -> list[dict]:
    await require_owned_portfolio(session, portfolio_id, user.id)
    snapshots = (
        await session.scalars(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshot.created_at.desc())
        )
    ).all()
    return [snapshot_payload(snapshot) for snapshot in snapshots]
