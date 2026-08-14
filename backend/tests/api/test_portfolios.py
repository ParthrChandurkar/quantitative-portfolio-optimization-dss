from __future__ import annotations

from decimal import Decimal

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OptimizationRun, Portfolio, PortfolioSnapshot, Report, User


async def test_stocks_sectors_and_portfolio_crud(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    seeded_market: tuple[str, ...],
) -> None:
    stocks = await client.get("/api/v1/stocks", headers=auth_headers)
    assert [row["symbol"] for row in stocks.json()["data"]] == sorted(seeded_market)
    filtered = await client.get("/api/v1/stocks?sector=IT", headers=auth_headers)
    assert len(filtered.json()["data"]) == 1
    assert len((await client.get("/api/v1/sectors", headers=auth_headers)).json()["data"]) == 4

    created = await client.post(
        "/api/v1/portfolios", json={"name": "My Portfolio"}, headers=auth_headers
    )
    assert created.status_code == 201
    portfolio_id = created.json()["data"]["id"]
    assert created.json()["data"]["latest_snapshot"] is None
    assert len((await client.get("/api/v1/portfolios", headers=auth_headers)).json()["data"]) == 1
    detail = await client.get(f"/api/v1/portfolios/{portfolio_id}", headers=auth_headers)
    assert detail.json()["data"]["name"] == "My Portfolio"
    patched = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=auth_headers,
        json={"name": "Renamed", "is_active": False},
    )
    assert patched.json()["data"]["name"] == "Renamed"
    assert not patched.json()["data"]["is_active"]
    snapshots = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/snapshots", headers=auth_headers
    )
    assert snapshots.json()["data"] == []


async def test_all_owned_resources_return_403_for_another_user(
    client: httpx.AsyncClient,
    session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    other = User(
        email="other@example.com",
        password_hash="hash",
        full_name="Other User",
    )
    session.add(other)
    await session.flush()
    portfolio = Portfolio(user_id=other.id, name="Private", is_active=True)
    session.add(portfolio)
    await session.flush()
    run = OptimizationRun(
        portfolio_id=portfolio.id,
        solver_used="SciPy",
        budget=Decimal(1000),
        target_return=Decimal("0.10"),
        risk_tolerance=None,
        max_single_weight=Decimal("0.50"),
        min_holdings=1,
        sector_constraints={},
        status="solved",
    )
    session.add(run)
    await session.flush()
    snapshot = PortfolioSnapshot(
        portfolio_id=portfolio.id,
        optimization_run_id=run.id,
        label="Private snapshot",
        is_baseline=True,
    )
    session.add(snapshot)
    await session.flush()
    report = Report(
        user_id=other.id,
        snapshot_id=snapshot.id,
        report_type="portfolio_summary",
        file_path="private.pdf",
    )
    session.add(report)
    await session.commit()

    cases = [
        ("GET", f"/api/v1/portfolios/{portfolio.id}", None),
        ("PATCH", f"/api/v1/portfolios/{portfolio.id}", {"name": "No"}),
        (
            "POST",
            f"/api/v1/portfolios/{portfolio.id}/optimize",
            {"budget": 1000, "target_return": 0.1},
        ),
        ("GET", f"/api/v1/optimization-runs/{run.id}", None),
        ("GET", f"/api/v1/portfolios/{portfolio.id}/snapshots", None),
        (
            "POST",
            f"/api/v1/portfolios/{portfolio.id}/scenarios",
            {
                "base_snapshot_id": str(snapshot.id),
                "scenario_type": "MARKET_CRASH",
                "params": {"delta": -0.2},
            },
        ),
        (
            "GET",
            f"/api/v1/portfolios/{portfolio.id}/snapshots/{snapshot.id}/analytics",
            None,
        ),
        (
            "POST",
            f"/api/v1/portfolios/{portfolio.id}/snapshots/{snapshot.id}/reports",
            {"report_type": "portfolio_summary"},
        ),
        ("GET", f"/api/v1/reports/{report.id}/download", None),
    ]
    for method, path, body in cases:
        response = await client.request(method, path, headers=auth_headers, json=body)
        assert response.status_code == 403, (path, response.text)
