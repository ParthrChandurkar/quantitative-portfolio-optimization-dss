from __future__ import annotations

import uuid
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Report, User


async def test_report_generate_history_and_download_routes(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    optimized: dict,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("REPORT_STORAGE_ROOT", str(tmp_path / "reports"))
    generated = await client.post(
        f"/api/v1/portfolios/{optimized['portfolio_id']}/snapshots/{optimized['snapshot_id']}/reports",
        headers=auth_headers,
        json={"report_type": "portfolio_summary"},
    )
    assert generated.status_code == 201, generated.text
    report = generated.json()["data"]
    history = await client.get("/api/v1/reports", headers=auth_headers)
    assert history.json()["data"][0]["id"] == report["id"]
    download = await client.get(
        f"/api/v1/reports/{report['id']}/download", headers=auth_headers
    )
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF-")


async def test_missing_owned_report_artifact_returns_structured_404(
    client: httpx.AsyncClient,
    session: AsyncSession,
    auth_headers: dict[str, str],
    optimized: dict,
) -> None:
    owner = await session.scalar(select(User).where(User.email == "owner@example.com"))
    assert owner is not None
    report = Report(
        user_id=owner.id,
        snapshot_id=uuid.UUID(optimized["snapshot_id"]),
        report_type="portfolio_summary",
        file_path="deliberately-missing-phase9-report.pdf",
    )
    session.add(report)
    await session.commit()
    response = await client.get(
        f"/api/v1/reports/{report.id}/download", headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REPORT_FILE_MISSING"
