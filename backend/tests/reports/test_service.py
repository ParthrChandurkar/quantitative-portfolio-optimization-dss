from __future__ import annotations

import uuid
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OptimizationRun, Portfolio, PortfolioSnapshot, Report, User
from app.reports.context_builder import ReportContext
from app.reports.service import ReportType, generate_report
from app.reports.storage import LocalDiskStorage, default_storage


async def test_generate_report_writes_valid_pdf_and_history_row(
    session: AsyncSession,
    tmp_path: Path,
    monkeypatch,
    report_context: ReportContext,
) -> None:
    user_id, portfolio_id, run_id, snapshot_id = (uuid.uuid4() for _ in range(4))
    session.add(
        User(
            id=user_id,
            email="pdf@example.com",
            password_hash="hash",
            full_name="PDF Investor",
        )
    )
    session.add(
        Portfolio(
            id=portfolio_id,
            user_id=user_id,
            name="PDF Portfolio",
            is_active=True,
        )
    )
    session.add(
        OptimizationRun(
            id=run_id,
            portfolio_id=portfolio_id,
            solver_used="SciPy",
            budget=Decimal(100000),
            target_return=Decimal("0.10"),
            risk_tolerance=None,
            max_single_weight=Decimal("0.60"),
            min_holdings=2,
            sector_constraints={},
            status="OPTIMAL",
        )
    )
    session.add(
        PortfolioSnapshot(
            id=snapshot_id,
            portfolio_id=portfolio_id,
            optimization_run_id=run_id,
            label="PDF snapshot",
            is_baseline=True,
        )
    )
    await session.commit()

    async def fake_load_context(*_args, **_kwargs) -> ReportContext:
        return report_context

    monkeypatch.setattr("app.reports.service.load_report_context", fake_load_context)
    storage = LocalDiskStorage(tmp_path / "reports", "/downloads")
    result = await generate_report(
        snapshot_id,
        ReportType.PORTFOLIO_SUMMARY,
        user_id,
        session=session,
        storage=storage,
    )

    pdf_path = tmp_path / "reports" / Path(result.file_path)
    pdf = pdf_path.read_bytes()
    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert len(PdfReader(BytesIO(pdf)).pages) == 1
    assert result.size_bytes == len(pdf) > 1_000
    assert result.download_url.startswith("/downloads/")

    row = await session.scalar(select(Report).where(Report.id == result.report_id))
    assert row is not None
    assert row.user_id == user_id
    assert row.snapshot_id == snapshot_id
    assert row.report_type == ReportType.PORTFOLIO_SUMMARY.value
    assert row.file_path == result.file_path


async def test_local_storage_rejects_unsafe_key(tmp_path: Path) -> None:
    storage = LocalDiskStorage(tmp_path)
    try:
        await storage.put("../escape.pdf", b"%PDF-test", "application/pdf")
    except ValueError as error:
        assert "safe relative" in str(error)
    else:
        raise AssertionError("unsafe storage key was accepted")

    try:
        await storage.put("report.txt", b"text", "text/plain")
    except ValueError as error:
        assert "PDF content only" in str(error)
    else:
        raise AssertionError("non-PDF content was accepted")


async def test_default_storage_uses_configured_root(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "configured-reports"
    monkeypatch.setenv("REPORT_STORAGE_ROOT", str(root))
    storage = default_storage()
    stored = await storage.put("test.pdf", b"%PDF-test", "application/pdf")
    assert stored.location == "test.pdf"
    assert (root / "test.pdf").exists()
