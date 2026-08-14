from __future__ import annotations

import httpx


async def test_scenario_route_reuses_phase6_and_returns_comparison(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    optimized: dict,
) -> None:
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
    payload = response.json()["data"]
    assert payload["scenario_run_id"]
    assert payload["comparison"] is not None
    assert payload["explanations"] is not None
    assert payload["metadata"]["re_solved"] is True


async def test_market_crash_route_supplies_persisted_or_default_betas(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    optimized: dict,
) -> None:
    response = await client.post(
        f"/api/v1/portfolios/{optimized['portfolio_id']}/scenarios",
        headers=auth_headers,
        json={
            "base_snapshot_id": optimized["snapshot_id"],
            "scenario_type": "MARKET_CRASH",
            "params": {"delta": -0.20, "kappa_vol": 0.5},
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["status"] == "optimal"
    assert payload["comparison"] is not None
    assert len(payload["params"]["betas"]) == len(payload["comparison"]["holdings"])
