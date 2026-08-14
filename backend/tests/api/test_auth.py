from __future__ import annotations

import uuid

import httpx
import pytest


async def test_signup_login_refresh_logout_rotation_flow(
    client: httpx.AsyncClient,
) -> None:
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "flow@example.com",
            "password": "strong-password",
            "full_name": "Auth Flow",
        },
    )
    assert signup.status_code == 201
    first = signup.json()["data"]
    assert first["user"]["email"] == "flow@example.com"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "flow@example.com", "password": "strong-password"},
    )
    tokens = login.json()["data"]
    access = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (await client.get("/api/v1/me", headers=access)).status_code == 200

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    rotated = refresh.json()["data"]
    rotated_access = {"Authorization": f"Bearer {rotated['access_token']}"}
    assert (await client.get("/api/v1/me", headers=rotated_access)).status_code == 200
    assert (
        await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
    ).status_code == 401

    logout = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": rotated["refresh_token"]}
    )
    assert logout.status_code == 200
    rejected = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
    )
    assert rejected.status_code == 401
    assert rejected.json()["data"] is None


async def test_profile_update_and_invalid_token(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    updated = await client.patch(
        "/api/v1/me",
        headers=auth_headers,
        json={"full_name": "Updated Owner", "risk_profile_default": "balanced"},
    )
    assert updated.json()["data"]["full_name"] == "Updated Owner"
    invalid = await client.get(
        "/api/v1/me", headers={"Authorization": "Bearer invalid"}
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/api/v1/me", None),
        ("PATCH", "/api/v1/me", {}),
        ("GET", "/api/v1/stocks", None),
        ("GET", "/api/v1/sectors", None),
        ("GET", "/api/v1/portfolios", None),
        ("POST", "/api/v1/portfolios", {"name": "No auth"}),
        ("GET", f"/api/v1/portfolios/{uuid.uuid4()}", None),
        ("PATCH", f"/api/v1/portfolios/{uuid.uuid4()}", {}),
        (
            "POST",
            f"/api/v1/portfolios/{uuid.uuid4()}/optimize",
            {"budget": 1000, "target_return": 0.1},
        ),
        ("GET", f"/api/v1/optimization-runs/{uuid.uuid4()}", None),
        ("GET", f"/api/v1/portfolios/{uuid.uuid4()}/snapshots", None),
        (
            "POST",
            f"/api/v1/portfolios/{uuid.uuid4()}/scenarios",
            {
                "base_snapshot_id": str(uuid.uuid4()),
                "scenario_type": "MARKET_CRASH",
                "params": {"delta": -0.2},
            },
        ),
        (
            "GET",
            f"/api/v1/portfolios/{uuid.uuid4()}/snapshots/{uuid.uuid4()}/analytics",
            None,
        ),
        (
            "POST",
            f"/api/v1/portfolios/{uuid.uuid4()}/snapshots/{uuid.uuid4()}/reports",
            {"report_type": "portfolio_summary"},
        ),
        ("GET", "/api/v1/reports", None),
        ("GET", f"/api/v1/reports/{uuid.uuid4()}/download", None),
    ],
)
async def test_every_protected_route_rejects_missing_auth(
    client: httpx.AsyncClient, method: str, path: str, body: dict | None
) -> None:
    response = await client.request(method, path, json=body)
    assert response.status_code == 401, (path, response.text)
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
