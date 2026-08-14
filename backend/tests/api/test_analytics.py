from __future__ import annotations

import httpx


async def test_analytics_route_returns_all_dashboard_sections(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    optimized: dict,
) -> None:
    response = await client.get(
        f"/api/v1/portfolios/{optimized['portfolio_id']}/snapshots/{optimized['snapshot_id']}/analytics",
        headers=auth_headers,
        params={"horizon_years": 3, "estimation_end_date": "2025-01-04"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["allocation"]
    assert payload["methodology"]["label"] == "OUT-OF-SAMPLE BACKTEST"
    assert payload["methodology"]["windows_overlap"] is False
    assert payload["risk_return"]
    assert payload["growth_projection"]
    assert payload["performance"]["buy_and_hold"]["points"]
    assert payload["risk_metrics"]
    assert payload["efficient_frontier"]
    assert payload["sector_distribution"]
