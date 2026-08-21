from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import AppSettings, CurrentUser, DBSession
from app.schemas.common import success
from app.schemas.optimization import OptimizeRequest
from app.services import optimization_service

router = APIRouter(tags=["optimization"])


@router.post("/portfolios/{portfolio_id}/optimize")
async def optimize(
    portfolio_id: uuid.UUID,
    request: OptimizeRequest,
    session: DBSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    return success(
        await optimization_service.optimize_portfolio(
            session=session,
            user=user,
            portfolio_id=portfolio_id,
            request=request,
            settings=settings,
        )
    )


@router.get("/optimization-runs/{run_id}")
async def get_run(run_id: uuid.UUID, session: DBSession, user: CurrentUser) -> dict:
    return success(
        await optimization_service.get_optimization_run(session, user, run_id)
    )
