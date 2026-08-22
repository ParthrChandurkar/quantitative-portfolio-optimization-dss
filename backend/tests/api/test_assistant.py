import httpx
from sqlalchemy import func, select

from app.db.models import AssistantQueryLog


async def test_assistant_route_answers_from_snapshot_and_logs_query(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    optimized: dict,
    session,
) -> None:
    response = await client.post(
        f"/api/v1/portfolios/{optimized['portfolio_id']}/assistant/ask",
        headers=auth_headers,
        json={"question": "why is the portfolio allocated this way"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["intent"] == "ALLOCATION_RATIONALE"
    assert payload["grounding"][0]["source"] == "explainability.portfolio_summary"
    assert payload["is_fallback"] is False
    assert (
        await session.scalar(select(func.count()).select_from(AssistantQueryLog)) == 1
    )


async def test_assistant_route_enforces_auth_and_ownership(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    import uuid

    portfolio_id = uuid.uuid4()
    assert (
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/assistant/ask",
            json={"question": "how risky is this"},
        )
    ).status_code == 401
    assert (
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/assistant/ask",
            headers=auth_headers,
            json={"question": "how risky is this"},
        )
    ).status_code == 403
