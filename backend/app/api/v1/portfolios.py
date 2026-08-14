from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DBSession
from app.schemas.common import success
from app.schemas.portfolios import PortfolioCreateRequest, PortfolioUpdateRequest
from app.services import portfolio_service

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("")
async def list_portfolios(session: DBSession, user: CurrentUser) -> dict:
    return success(await portfolio_service.list_portfolios(session, user))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    request: PortfolioCreateRequest, session: DBSession, user: CurrentUser
) -> dict:
    return success(await portfolio_service.create_portfolio(session, user, request))


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> dict:
    return success(
        await portfolio_service.get_portfolio(session, user, portfolio_id)
    )


@router.patch("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: uuid.UUID,
    request: PortfolioUpdateRequest,
    session: DBSession,
    user: CurrentUser,
) -> dict:
    return success(
        await portfolio_service.update_portfolio(
            session, user, portfolio_id, request
        )
    )


@router.get("/{portfolio_id}/snapshots")
async def list_snapshots(
    portfolio_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> dict:
    return success(
        await portfolio_service.list_snapshots(session, user, portfolio_id)
    )
