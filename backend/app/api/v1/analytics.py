from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.analytics import walk_forward_service
from app.analytics.backtest import RebalanceFrequency
from app.core.deps import AppSettings, CurrentUser, DBSession
from app.schemas.common import success
from app.schemas.walk_forward import WalkForwardRequest
from app.services import analytics_service

router = APIRouter(tags=["analytics"])


@router.post("/portfolios/{portfolio_id}/walk-forward")
async def create_walk_forward_run(
    portfolio_id: uuid.UUID,
    request: WalkForwardRequest,
    session: DBSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    return success(
        await walk_forward_service.run_walk_forward(
            session,
            user,
            settings,
            portfolio_id,
            request.start_date,
            request.end_date,
            RebalanceFrequency(request.rebalance_frequency),
            request.lookback_days,
        )
    )


@router.get("/portfolios/{portfolio_id}/walk-forward/{run_id}")
async def get_walk_forward_run(
    portfolio_id: uuid.UUID,
    run_id: uuid.UUID,
    session: DBSession,
    user: CurrentUser,
) -> dict:
    return success(
        await walk_forward_service.get_walk_forward_run(
            session, user, portfolio_id, run_id
        )
    )


@router.get("/portfolios/{portfolio_id}/snapshots/{snapshot_id}/analytics")
async def get_analytics(
    portfolio_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    session: DBSession,
    user: CurrentUser,
    settings: AppSettings,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    horizon_years: Annotated[int, Query(ge=0, le=50)] = 10,
    estimation_end_date: Annotated[date | None, Query()] = None,
) -> dict:
    return success(
        await analytics_service.get_snapshot_analytics(
            session,
            user,
            portfolio_id,
            snapshot_id,
            settings,
            start_date=start_date,
            end_date=end_date,
            horizon_years=horizon_years,
            estimation_end_date=estimation_end_date,
        )
    )
