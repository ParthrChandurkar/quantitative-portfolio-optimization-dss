"""Orchestration service for persisted OptiVest PDF reports."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsDateRange
from app.db.models import Report
from app.reports.context_builder import load_report_context
from app.reports.pdf_renderer import render_pdf
from app.reports.storage import ReportStorage, default_storage


class ReportType(StrEnum):
    PORTFOLIO_SUMMARY = "portfolio_summary"
    OPTIMIZATION_REPORT = "optimization_report"
    INVESTMENT_RECOMMENDATION = "investment_recommendation"


TEMPLATE_BY_TYPE: dict[ReportType, str] = {
    ReportType.PORTFOLIO_SUMMARY: "summary.html.jinja",
    ReportType.OPTIMIZATION_REPORT: "optimization_report.html.jinja",
    ReportType.INVESTMENT_RECOMMENDATION: "recommendation.html.jinja",
}


@dataclass(frozen=True, slots=True)
class ReportResult:
    report_id: uuid.UUID
    report_type: ReportType
    file_path: str
    download_url: str
    size_bytes: int


async def generate_report(
    snapshot_id: uuid.UUID,
    report_type: ReportType,
    user_id: uuid.UUID,
    *,
    session: AsyncSession,
    storage: ReportStorage | None = None,
    date_range: AnalyticsDateRange | None = None,
) -> ReportResult:
    """Build context, render, store, and persist one report-history row."""

    context = await load_report_context(session, snapshot_id, user_id, date_range)
    pdf = await render_pdf(TEMPLATE_BY_TYPE[report_type], context)
    report_id = uuid.uuid4()
    key = f"{user_id}/{snapshot_id}/{report_id}-{report_type.value}.pdf"
    stored = await (storage or default_storage()).put(key, pdf, "application/pdf")
    row = Report(
        id=report_id,
        user_id=user_id,
        snapshot_id=snapshot_id,
        report_type=report_type.value,
        file_path=stored.location,
    )
    session.add(row)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return ReportResult(
        report_id=report_id,
        report_type=report_type,
        file_path=stored.location,
        download_url=stored.download_url,
        size_bytes=stored.size_bytes,
    )
