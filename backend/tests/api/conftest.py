from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.deps import get_db
from app.db.models import Sector, Stock, StockPrice
from main import create_app


@pytest.fixture
def api_settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite://",
        JWT_SECRET="phase9-test-secret-with-sufficient-entropy",
        JWT_ACCESS_EXPIRY=600,
        JWT_REFRESH_EXPIRY=3600,
        COVARIANCE_LOOKBACK_DAYS=20,
        DEBUG=True,
    )


@pytest_asyncio.fixture
async def client(
    session: AsyncSession, api_settings: Settings
) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app()

    async def override_db():
        yield session

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_settings] = lambda: api_settings
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
        yield api


@pytest_asyncio.fixture
async def auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "owner@example.com",
            "password": "strong-password",
            "full_name": "Portfolio Owner",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


@pytest_asyncio.fixture
async def seeded_market(session: AsyncSession) -> tuple[str, ...]:
    sectors = [Sector(name=name) for name in ("IT", "Energy", "Banking", "FMCG")]
    stocks = [
        Stock(symbol=symbol, company_name=f"{symbol} Ltd", sector=sector)
        for symbol, sector in zip(("ALPHA", "BETA", "GAMMA", "DELTA"), sectors, strict=True)
    ]
    session.add_all([*sectors, *stocks])
    await session.flush()
    start = date(2025, 1, 1)
    returns = (
        ("0.001", "0.004", "-0.001", "0.002"),
        ("0.003", "-0.002", "0.002", "0.001"),
        ("-0.001", "0.003", "0.001", "0.002"),
        ("0.002", "0.001", "0.004", "-0.001"),
        ("0.004", "0.002", "-0.002", "0.003"),
        ("0.001", "-0.001", "0.003", "0.002"),
    )
    for day, row_returns in enumerate(returns):
        for index, (stock, daily_return) in enumerate(
            zip(stocks, row_returns, strict=True)
        ):
            price = Decimal(100 + index + day)
            session.add(
                StockPrice(
                    stock_id=stock.id,
                    trade_date=start + timedelta(days=day),
                    open=price,
                    high=price + 1,
                    low=price - 1,
                    close=price,
                    adj_close=price,
                    volume=10_000,
                    daily_return=None if day == 0 else Decimal(daily_return),
                )
            )
    await session.commit()
    return tuple(stock.symbol for stock in stocks)


@pytest_asyncio.fixture
async def optimized(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    seeded_market: tuple[str, ...],
) -> dict:
    portfolio_response = await client.post(
        "/api/v1/portfolios", json={"name": "API Portfolio"}, headers=auth_headers
    )
    portfolio_id = portfolio_response.json()["data"]["id"]
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/optimize",
        headers=auth_headers,
        json={
            "budget": 100000,
            "target_return": 0.20,
            "max_single_weight": 0.60,
            "sector_caps": {name: 0.60 for name in ("IT", "Energy", "Banking", "FMCG")},
            "default_sector_cap": 0.60,
            "solver": "SciPy",
            "lookback_days": 5,
            "label": "API optimized snapshot",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["run"]["status"] == "solved", payload
    return {
        "portfolio_id": portfolio_id,
        "run_id": payload["run"]["id"],
        "snapshot_id": payload["snapshot"]["id"],
        "payload": payload,
    }
