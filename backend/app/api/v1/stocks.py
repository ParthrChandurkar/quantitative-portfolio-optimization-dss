from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DBSession
from app.schemas.common import success
from app.services import market_service

router = APIRouter(tags=["market-data"])


@router.get("/stocks")
async def get_stocks(
    session: DBSession,
    _user: CurrentUser,
    sector: str | None = Query(default=None),
) -> dict:
    return success(await market_service.list_stocks(session, sector))


@router.get("/sectors")
async def get_sectors(session: DBSession, _user: CurrentUser) -> dict:
    return success(await market_service.list_sectors(session))
