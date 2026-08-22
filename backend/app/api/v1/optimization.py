from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncEngine

from app.alerts.service import check_alerts_in_background
from app.core.deps import AppSettings, CurrentUser, DBSession
from app.schemas.common import success
from app.schemas.optimization import OptimizeRequest
from app.services import optimization_service

router = APIRouter(tags=["optimization"])


@router.post("/portfolios/{portfolio_id}/optimize")
async def optimize(
    portfolio_id: uuid.UUID,
    request: OptimizeRequest,
    background_tasks: BackgroundTasks,
    session: DBSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    result = await optimization_service.optimize_portfolio(
        session=session,
        user=user,
        portfolio_id=portfolio_id,
        request=request,
        settings=settings,
    )
    if result["run"]["status"] == "solved":
        engine = session.bind
        if not isinstance(engine, AsyncEngine):
            raise RuntimeError("The request session is not bound to an async engine")
        background_tasks.add_task(
            check_alerts_in_background, engine, user.id, portfolio_id
        )
    return success(result)


@router.get("/optimization-runs/{run_id}")
async def get_run(run_id: uuid.UUID, session: DBSession, user: CurrentUser) -> dict:
    return success(
        await optimization_service.get_optimization_run(session, user, run_id)
    )
