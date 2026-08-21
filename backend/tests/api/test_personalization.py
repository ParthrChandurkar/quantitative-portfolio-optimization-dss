from __future__ import annotations

import httpx

ANSWERS = {
    "age_bracket": "30_44",
    "investment_horizon": "6_10_years",
    "income_stability": "stable",
    "loss_reaction": "hold",
    "experience_level": "intermediate",
    "financial_dependents": "one_or_two",
}


async def test_authenticated_prediction_persistence_and_latest_retrieval(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    missing = await client.get("/api/v1/me/risk-profile", headers=auth_headers)
    assert missing.status_code == 404

    created = await client.post(
        "/api/v1/me/risk-profile", headers=auth_headers, json={"answers": ANSWERS}
    )
    assert created.status_code == 200, created.text
    payload = created.json()["data"]
    assert payload["predicted_category"] == "moderate"
    assert payload["recommended_constraints"] == {
        "risk_tolerance": 0.22,
        "max_single_weight": 0.15,
        "default_sector_cap": 0.30,
    }
    assert 0.0 <= payload["category_confidence"] <= 1.0
    assert payload["questionnaire_answers"] == ANSWERS

    latest = await client.get("/api/v1/me/risk-profile", headers=auth_headers)
    assert latest.status_code == 200
    assert latest.json()["data"]["id"] == payload["id"]
    profile = await client.get("/api/v1/me", headers=auth_headers)
    assert profile.json()["data"]["risk_profile_default"] == "moderate"


async def test_personalization_routes_require_auth(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/me/risk-profile")).status_code == 401
    assert (
        await client.post("/api/v1/me/risk-profile", json={"answers": ANSWERS})
    ).status_code == 401


async def test_profiles_are_scoped_to_the_authenticated_user(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    assert (
        await client.post(
            "/api/v1/me/risk-profile",
            headers=auth_headers,
            json={"answers": ANSWERS},
        )
    ).status_code == 200
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "second-risk-user@example.com",
            "password": "strong-password",
            "full_name": "Second Risk User",
        },
    )
    second_headers = {
        "Authorization": f"Bearer {signup.json()['data']['access_token']}"
    }
    second_profile = await client.get(
        "/api/v1/me/risk-profile", headers=second_headers
    )
    assert second_profile.status_code == 404
    assert second_profile.json()["error"]["code"] == "RISK_PROFILE_NOT_FOUND"
