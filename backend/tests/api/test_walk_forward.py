from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import httpx
import pytest


def _payload(portfolio_id, run_id) -> dict:
    return {
        "id": run_id,
        "portfolio_id": portfolio_id,
        "rebalance_frequency": "monthly",
        "lookback_days": 252,
        "start_date": date(2025, 1, 30),
        "end_date": date(2026, 1, 30),
        "constraints_snapshot": {},
        "result": {"methodology": {"strict_pre_rebalance_estimation": True}},
        "created_at": datetime.now(UTC),
    }


@pytest.mark.asyncio
async def test_walk_forward_routes_use_envelope_and_typed_request(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portfolio_id, run_id = uuid4(), uuid4()
    called = {}

    async def fake_run(
        _session,
        _user,
        _settings,
        selected_portfolio,
        start_date,
        end_date,
        frequency,
        lookback_days,
    ):
        called["request"] = (
            selected_portfolio,
            start_date,
            end_date,
            frequency.value,
            lookback_days,
        )
        return _payload(portfolio_id, run_id)

    async def fake_get(_session, _user, selected_portfolio, selected_run):
        called["get"] = (selected_portfolio, selected_run)
        return _payload(portfolio_id, run_id)

    monkeypatch.setattr(
        "app.api.v1.analytics.walk_forward_service.run_walk_forward", fake_run
    )
    monkeypatch.setattr(
        "app.api.v1.analytics.walk_forward_service.get_walk_forward_run", fake_get
    )
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/walk-forward",
        headers=auth_headers,
        json={
            "start_date": "2025-01-30",
            "end_date": "2026-01-30",
            "rebalance_frequency": "monthly",
            "lookback_days": 252,
        },
    )
    assert response.status_code == 200
    assert response.json()["error"] is None
    assert response.json()["data"]["id"] == str(run_id)
    assert called["request"] == (
        portfolio_id,
        date(2025, 1, 30),
        date(2026, 1, 30),
        "monthly",
        252,
    )

    fetched = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/walk-forward/{run_id}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200
    assert called["get"] == (portfolio_id, run_id)


async def test_walk_forward_request_rejects_reversed_dates(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        f"/api/v1/portfolios/{uuid4()}/walk-forward",
        headers=auth_headers,
        json={"start_date": "2026-01-30", "end_date": "2025-01-30"},
    )
    assert response.status_code == 422
