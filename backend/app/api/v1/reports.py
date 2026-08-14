from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from fastapi.responses import Response

from app.core.deps import CurrentUser, DBSession
from app.schemas.common import success
from app.schemas.reports import ReportCreateRequest
from app.services import report_service

router = APIRouter(tags=["reports"])


@router.post(
    "/portfolios/{portfolio_id}/snapshots/{snapshot_id}/reports",
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    portfolio_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    request: ReportCreateRequest,
    session: DBSession,
    user: CurrentUser,
) -> dict:
    return success(
        await report_service.create_report(
            session, user, portfolio_id, snapshot_id, request.report_type
        )
    )


@router.get("/reports")
async def list_reports(session: DBSession, user: CurrentUser) -> dict:
    return success(await report_service.list_reports(session, user))


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> Response:
    content, filename = await report_service.download_report(session, user, report_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
