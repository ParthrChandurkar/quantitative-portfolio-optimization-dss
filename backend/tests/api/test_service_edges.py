from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.optimization.types import OptimizationResult, OptimizationStatus, SolverName
from app.services.analytics_service import snapshot_holdings
from app.services.problem_service import (
    build_problem,
    decode_constraint_config,
    latest_market_date,
    stock_universe,
)


async def test_auth_rejects_duplicate_bad_credentials_and_malformed_refresh(
    client: httpx.AsyncClient,
) -> None:
    signup_body = {
        "email": "edge-auth@example.com",
        "password": "strong-password",
        "full_name": "Edge Auth",
    }
    assert (await client.post("/api/v1/auth/signup", json=signup_body)).status_code == 201
    duplicate = await client.post("/api/v1/auth/signup", json=signup_body)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_EXISTS"

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": signup_body["email"], "password": "incorrect-password"},
    )
    assert bad_login.status_code == 401
    for path in ("refresh", "logout"):
        response = await client.post(
            f"/api/v1/auth/{path}", json={"refresh_token": "not-a-jwt"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


async def test_service_error_paths_and_legacy_constraint_document(
    client: httpx.AsyncClient,
    session: AsyncSession,
    auth_headers: dict[str, str],
    seeded_market: tuple[str, ...],
) -> None:
    missing_run = await client.get(
        f"/api/v1/optimization-runs/{uuid.uuid4()}", headers=auth_headers
    )
    assert missing_run.status_code == 403

    legacy = decode_constraint_config({"IT": 0.4, "Energy": 0.3})
    assert legacy["caps"] == {"IT": 0.4, "Energy": 0.3}
    assert legacy["max_holdings"] is None

    with pytest.raises(ValueError, match="no market data"):
        await latest_market_date(session, (uuid.uuid4(),))
    with pytest.raises(ValueError, match="requested stocks are missing"):
        await stock_universe(session, (seeded_market[0], "DOES_NOT_EXIST"))
    with pytest.raises(ValueError, match="no holdings"):
        await snapshot_holdings(session, uuid.uuid4())
    with pytest.raises(ValueError, match="at least two stocks"):
        await build_problem(
            session,
            Settings(
                DATABASE_URL="sqlite+aiosqlite://",
                JWT_SECRET="service-edge-test-secret-with-sufficient-entropy",
            ),
            symbols=(seeded_market[0],),
            budget=100_000,
            target_return=0.10,
            risk_tolerance=None,
            max_single_weight=1.0,
            sector_caps={},
            default_sector_cap=1.0,
            min_holdings=None,
            max_holdings=None,
            min_lot_weight=0.01,
            risk_free_rate=0.0,
            solver=SolverName.SCIPY,
        )

    own_portfolio = await client.post(
        "/api/v1/portfolios", headers=auth_headers, json={"name": "Snapshot edge"}
    )
    mismatch = await client.get(
        f"/api/v1/portfolios/{own_portfolio.json()['data']['id']}/snapshots/{uuid.uuid4()}/analytics",
        headers=auth_headers,
    )
    assert mismatch.status_code == 403


@pytest.mark.parametrize(
    ("solver_status", "persisted_status"),
    [
        (OptimizationStatus.INFEASIBLE, "infeasible"),
        (OptimizationStatus.FAILED, "failed"),
    ],
)
async def test_optimization_failure_statuses_are_persisted_and_pollable(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    seeded_market: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
    solver_status: OptimizationStatus,
    persisted_status: str,
) -> None:
    del seeded_market
    portfolio = await client.post(
        "/api/v1/portfolios", headers=auth_headers, json={"name": persisted_status}
    )
    portfolio_id = portfolio.json()["data"]["id"]

    def fake_solve(_problem) -> OptimizationResult:
        return OptimizationResult(
            status=solver_status,
            solver_used=SolverName.SCIPY,
            weights={},
            objective_value=None,
            expected_return=None,
            expected_variance=None,
            expected_volatility=None,
            solve_time_ms=1,
            message=f"synthetic {persisted_status}",
        )

    monkeypatch.setattr("app.services.optimization_service.solve", fake_solve)
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/optimize",
        headers=auth_headers,
        json={
            "budget": 100_000,
            "target_return": 0.10,
            "max_single_weight": 0.60,
            "default_sector_cap": 0.60,
            "solver": "SciPy",
            "lookback_days": 5,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["run"]["status"] == persisted_status
    assert response.json()["data"]["snapshot"] is None
    run_id = response.json()["data"]["run"]["id"]
    poll = await client.get(
        f"/api/v1/optimization-runs/{run_id}", headers=auth_headers
    )
    assert poll.json()["data"]["status"] == persisted_status
