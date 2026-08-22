from __future__ import annotations

import asyncio
import time
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncEngine

from app.alerts.service import check_alerts_in_background
from app.api.v1.optimization import optimize
from app.api.v1.scenarios import run_scenario


async def test_optimize_response_does_not_wait_for_alert_check(
    monkeypatch, engine: AsyncEngine
) -> None:
    portfolio_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4())
    session = SimpleNamespace(bind=engine)
    solved = {
        "run": {"status": "solved"},
        "snapshot": {"id": str(uuid.uuid4())},
        "explanations": {},
    }

    async def slow_alert_check(*_args) -> None:
        await asyncio.sleep(10)

    monkeypatch.setattr(
        "app.api.v1.optimization.optimization_service.optimize_portfolio",
        AsyncMock(return_value=solved),
    )
    monkeypatch.setattr(
        "app.api.v1.optimization.check_alerts_in_background", slow_alert_check
    )
    background_tasks = BackgroundTasks()

    started = time.perf_counter()
    response = await optimize(
        portfolio_id,
        SimpleNamespace(),
        background_tasks,
        session,
        user,
        SimpleNamespace(),
    )
    elapsed = time.perf_counter() - started

    assert response["data"]["run"]["status"] == "solved"
    assert elapsed < 0.1
    assert len(background_tasks.tasks) == 1


async def test_unsolved_optimize_does_not_schedule_alerts(
    monkeypatch, engine: AsyncEngine
) -> None:
    monkeypatch.setattr(
        "app.api.v1.optimization.optimization_service.optimize_portfolio",
        AsyncMock(
            return_value={
                "run": {"status": "infeasible"},
                "snapshot": None,
                "explanations": None,
            }
        ),
    )
    tasks = BackgroundTasks()
    await optimize(
        uuid.uuid4(),
        SimpleNamespace(),
        tasks,
        SimpleNamespace(bind=engine),
        SimpleNamespace(id=uuid.uuid4()),
        SimpleNamespace(),
    )
    assert tasks.tasks == []


async def test_solved_optimize_rejects_non_async_engine(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.optimization.optimization_service.optimize_portfolio",
        AsyncMock(return_value={"run": {"status": "solved"}}),
    )
    with pytest.raises(RuntimeError, match="not bound to an async engine"):
        await optimize(
            uuid.uuid4(),
            SimpleNamespace(),
            BackgroundTasks(),
            SimpleNamespace(bind=object()),
            SimpleNamespace(id=uuid.uuid4()),
            SimpleNamespace(),
        )


async def test_feasible_scenario_schedules_alerts_without_waiting(
    monkeypatch, engine: AsyncEngine
) -> None:
    result = {"comparison": {"metric_deltas": {}}, "status": "optimal"}
    monkeypatch.setattr(
        "app.api.v1.scenarios.scenario_service.run_portfolio_scenario",
        AsyncMock(return_value=result),
    )
    tasks = BackgroundTasks()
    response = await run_scenario(
        uuid.uuid4(),
        SimpleNamespace(),
        tasks,
        SimpleNamespace(bind=engine),
        SimpleNamespace(id=uuid.uuid4()),
        SimpleNamespace(),
    )
    assert response["data"] == result
    assert len(tasks.tasks) == 1


async def test_feasible_scenario_rejects_non_async_engine(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.scenarios.scenario_service.run_portfolio_scenario",
        AsyncMock(return_value={"comparison": {}}),
    )
    with pytest.raises(RuntimeError, match="not bound to an async engine"):
        await run_scenario(
            uuid.uuid4(),
            SimpleNamespace(),
            BackgroundTasks(),
            SimpleNamespace(bind=object()),
            SimpleNamespace(id=uuid.uuid4()),
            SimpleNamespace(),
        )


async def test_background_alert_runner_uses_fresh_session(
    monkeypatch, engine: AsyncEngine
) -> None:
    check = AsyncMock(return_value=[])
    monkeypatch.setattr("app.alerts.service.check_alerts", check)
    user_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()

    await check_alerts_in_background(engine, user_id, portfolio_id)

    check.assert_awaited_once()
    background_session, actual_user, actual_portfolio = check.await_args.args
    assert background_session.bind is engine
    assert (actual_user, actual_portfolio) == (user_id, portfolio_id)


async def test_background_alert_failure_is_contained(
    monkeypatch, engine: AsyncEngine, caplog
) -> None:
    monkeypatch.setattr(
        "app.alerts.service.check_alerts",
        AsyncMock(side_effect=RuntimeError("detector unavailable")),
    )

    await check_alerts_in_background(engine, uuid.uuid4(), uuid.uuid4())

    assert "Background alert check failed" in caplog.text
