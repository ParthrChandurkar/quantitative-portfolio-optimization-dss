from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import AppSettings, CurrentUser, DBSession
from app.schemas.common import success
from app.schemas.scenarios import ScenarioRunRequest
from app.services import scenario_service

router = APIRouter(tags=["scenarios"])


@router.post("/portfolios/{portfolio_id}/scenarios")
async def run_scenario(
    portfolio_id: uuid.UUID,
    request: ScenarioRunRequest,
    session: DBSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    return success(
        await scenario_service.run_portfolio_scenario(
            session, user, portfolio_id, request, settings
        )
    )
