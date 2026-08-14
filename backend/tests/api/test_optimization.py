from __future__ import annotations

import os
import uuid

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.deps import get_db
from app.db.models import User
from main import create_app

REAL_DATABASE_URL = os.getenv("REAL_DATABASE_URL")


async def test_optimize_returns_snapshot_holdings_metrics_and_explanations_together(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    optimized: dict,
) -> None:
    payload = optimized["payload"]
    assert payload["snapshot"]["holdings"]
    assert payload["snapshot"]["expected_return"] is not None
    assert payload["snapshot"]["expected_volatility"] is not None
    assert payload["snapshot"]["sharpe_ratio"] is not None
    assert payload["explanations"]["summary"]
    assert payload["explanations"]["included"]

    poll = await client.get(
        f"/api/v1/optimization-runs/{optimized['run_id']}", headers=auth_headers
    )
    assert poll.json()["data"]["status"] == "solved"
    snapshots = await client.get(
        f"/api/v1/portfolios/{optimized['portfolio_id']}/snapshots",
        headers=auth_headers,
    )
    assert snapshots.json()["data"][0]["id"] == optimized["snapshot_id"]
    detail = await client.get(
        f"/api/v1/portfolios/{optimized['portfolio_id']}", headers=auth_headers
    )
    latest = detail.json()["data"]["latest_snapshot"]
    assert latest["id"] == optimized["snapshot_id"]
    assert latest["budget_inr"] == 100000
    assert latest["holdings"]
    assert latest["explanations"]["included"]
    assert latest["explanations"]["included"][0]["narrative_text"]


@pytest.mark.skipif(
    not REAL_DATABASE_URL,
    reason="set REAL_DATABASE_URL to exercise the API against loaded Nifty-50 data",
)
async def test_real_49_stock_optimization_through_http_api() -> None:
    """Exercise auth, ownership, market loading, solving, and persistence together."""

    assert REAL_DATABASE_URL is not None
    engine = create_async_engine(REAL_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        DATABASE_URL=REAL_DATABASE_URL,
        JWT_SECRET="phase9-real-integration-secret-with-sufficient-entropy",
        JWT_ACCESS_EXPIRY=600,
        JWT_REFRESH_EXPIRY=3600,
        COVARIANCE_LOOKBACK_DAYS=252,
        DEBUG=True,
    )
    application = create_app()

    async def override_db():
        async with factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_settings] = lambda: settings
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=True)
    email = f"phase9-{uuid.uuid4().hex}@example.com"
    user_id: uuid.UUID | None = None
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://phase9-integration"
        ) as client:
            signup = await client.post(
                "/api/v1/auth/signup",
                json={
                    "email": email,
                    "password": "real-data-integration-password",
                    "full_name": "Phase 9 Integration",
                },
            )
            assert signup.status_code == 201, signup.text
            user_id = uuid.UUID(signup.json()["data"]["user"]["id"])
            headers = {
                "Authorization": f"Bearer {signup.json()['data']['access_token']}"
            }
            portfolio = await client.post(
                "/api/v1/portfolios",
                headers=headers,
                json={"name": "Real Nifty-50 API integration"},
            )
            assert portfolio.status_code == 201, portfolio.text
            portfolio_id = portfolio.json()["data"]["id"]
            response = await client.post(
                f"/api/v1/portfolios/{portfolio_id}/optimize",
                headers=headers,
                json={
                    "budget": 1_000_000,
                    "risk_tolerance": 1.0,
                    "max_single_weight": 0.20,
                    "default_sector_cap": 0.35,
                    "solver": "SciPy",
                    "lookback_days": 252,
                    "label": "Real 49-stock integration snapshot",
                },
            )
            assert response.status_code == 200, response.text
            payload = response.json()["data"]
            assert payload["run"]["status"] == "solved", payload
            assert 0 <= payload["run"]["solve_time_ms"] < 5_000
            assert payload["snapshot"]["holdings"]
            assert payload["snapshot"]["expected_return"] is not None
            assert payload["snapshot"]["expected_volatility"] is not None
            assert payload["explanations"]["included"]
    finally:
        if user_id is not None:
            async with factory() as cleanup_session:
                await cleanup_session.execute(delete(User).where(User.id == user_id))
                await cleanup_session.commit()
        await engine.dispose()
