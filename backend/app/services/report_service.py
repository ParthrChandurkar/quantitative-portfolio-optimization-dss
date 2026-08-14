"""Owned report generation, history, and artifact download operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.db.models import Report, User
from app.reports.service import ReportType, generate_report
from app.reports.storage import ReportStorage, default_storage
from app.services.portfolio_service import require_owned_snapshot


async def create_report(
    session: AsyncSession,
    user: User,
    portfolio_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    report_type: ReportType,
    storage: ReportStorage | None = None,
) -> dict:
    await require_owned_snapshot(session, portfolio_id, snapshot_id, user.id)
    result = await generate_report(
        snapshot_id,
        report_type,
        user.id,
        session=session,
        storage=storage,
    )
    return {
        "id": result.report_id,
        "snapshot_id": snapshot_id,
        "report_type": result.report_type.value,
        "file_path": result.file_path,
        "download_url": result.download_url,
        "size_bytes": result.size_bytes,
    }


async def list_reports(
    session: AsyncSession, user: User, storage: ReportStorage | None = None
) -> list[dict]:
    backend = storage or default_storage()
    rows = (
        await session.scalars(
            select(Report)
            .where(Report.user_id == user.id)
            .order_by(Report.generated_at.desc())
        )
    ).all()
    return [
        {
            "id": row.id,
            "snapshot_id": row.snapshot_id,
            "report_type": row.report_type,
            "file_path": row.file_path,
            "generated_at": row.generated_at,
            "download_url": backend.url_for(row.file_path),
        }
        for row in rows
    ]


async def download_report(
    session: AsyncSession,
    user: User,
    report_id: uuid.UUID,
    storage: ReportStorage | None = None,
) -> tuple[bytes, str]:
    row = await session.get(Report, report_id)
    if row is None or row.user_id != user.id:
        raise APIError(403, "REPORT_FORBIDDEN", "You do not own this report")
    try:
        content = await (storage or default_storage()).get(row.file_path)
    except FileNotFoundError:
        raise APIError(404, "REPORT_FILE_MISSING", "The report file is unavailable") from None
    return content, f"OptiVest-{row.report_type}-{row.id}.pdf"
