from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncEngine

from app.alerts.service import check_alerts_in_background
from app.core.deps import AppSettings, CurrentUser, DBSession
from app.schemas.common import success
from app.schemas.scenarios import ScenarioRunRequest
from app.services import scenario_service

router = APIRouter(tags=["scenarios"])


@router.post("/portfolios/{portfolio_id}/scenarios")
async def run_scenario(
    portfolio_id: uuid.UUID,
    request: ScenarioRunRequest,
    background_tasks: BackgroundTasks,
    session: DBSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    result = await scenario_service.run_portfolio_scenario(
        session, user, portfolio_id, request, settings
    )
    if result["comparison"] is not None:
        engine = session.bind
        if not isinstance(engine, AsyncEngine):
            raise RuntimeError("The request session is not bound to an async engine")
        background_tasks.add_task(
            check_alerts_in_background, engine, user.id, portfolio_id
        )
    return success(result)
