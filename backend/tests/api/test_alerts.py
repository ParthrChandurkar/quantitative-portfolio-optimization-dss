import uuid
from unittest.mock import AsyncMock

from sqlalchemy import select

from app.db.models import Alert, Portfolio, User


async def test_alert_routes_list_acknowledge_and_check(
    client, auth_headers, optimized, session
) -> None:
    user = await session.scalar(select(User).where(User.email == "owner@example.com"))
    portfolio = await session.get(Portfolio, uuid.UUID(optimized["portfolio_id"]))
    alert = Alert(
        user_id=user.id,
        portfolio_id=portfolio.id,
        snapshot_id=uuid.UUID(optimized["snapshot_id"]),
        alert_type="RISK_DRIFT",
        severity="warning",
        message="Expected volatility is 0.31 and target is 0.22.",
        grounding={"expected_volatility": 0.31, "recommended_risk_tolerance": 0.22},
    )
    session.add(alert)
    await session.commit()

    listed = await client.get("/api/v1/me/alerts", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["data"][0]["id"] == str(alert.id)
    acknowledged = await client.patch(
        f"/api/v1/me/alerts/{alert.id}/acknowledge", headers=auth_headers
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["data"]["acknowledged"] is True
    checked = await client.post(
        f"/api/v1/portfolios/{portfolio.id}/alerts/check", headers=auth_headers
    )
    assert checked.status_code == 200
    assert checked.json()["data"] == []


async def test_alert_routes_require_auth_and_ownership(client, auth_headers) -> None:
    alert_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    assert (await client.get("/api/v1/me/alerts")).status_code == 401
    assert (
        await client.patch(
            f"/api/v1/me/alerts/{alert_id}/acknowledge", headers=auth_headers
        )
    ).status_code == 403
    assert (
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/alerts/check", headers=auth_headers
        )
    ).status_code == 403


async def test_successful_optimize_runs_alert_check_hook(
    client, auth_headers, seeded_market, monkeypatch
) -> None:
    check = AsyncMock(return_value=[])
    monkeypatch.setattr("app.api.v1.optimization.check_alerts_in_background", check)
    portfolio = await client.post(
        "/api/v1/portfolios", json={"name": "Hook Portfolio"}, headers=auth_headers
    )
    portfolio_id = portfolio.json()["data"]["id"]
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/optimize",
        headers=auth_headers,
        json={
            "budget": 100000,
            "target_return": 0.20,
            "max_single_weight": 0.60,
            "default_sector_cap": 0.60,
            "solver": "SciPy",
            "lookback_days": 5,
            "label": "Hook snapshot",
        },
    )
    assert response.status_code == 200, response.text
    check.assert_awaited_once()


async def test_successful_scenario_runs_alert_check_hook(
    client, auth_headers, optimized, monkeypatch
) -> None:
    check = AsyncMock(return_value=[])
    monkeypatch.setattr("app.api.v1.scenarios.check_alerts_in_background", check)
    response = await client.post(
        f"/api/v1/portfolios/{optimized['portfolio_id']}/scenarios",
        headers=auth_headers,
        json={
            "base_snapshot_id": optimized["snapshot_id"],
            "scenario_type": "BUDGET_INCREASE",
            "params": {"new_budget": 120000},
        },
    )
    assert response.status_code == 200, response.text
    check.assert_awaited_once()
