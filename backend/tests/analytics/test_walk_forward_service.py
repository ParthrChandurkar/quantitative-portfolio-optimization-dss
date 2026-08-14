from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.analytics.backtest import (
    BacktestMode,
    BacktestPoint,
    BacktestResult,
    RebalanceFrequency,
)
from app.analytics.walk_forward import (
    WalkForwardPeriod,
    WalkForwardPoint,
    WalkForwardSimulation,
)
from app.analytics.walk_forward_service import get_walk_forward_run, run_walk_forward
from app.core.config import Settings
from app.db.models import OptimizationRun, Portfolio, User, WalkForwardRun
from app.optimization.types import (
    OptimizationInput,
    OptimizationResult,
    OptimizationStatus,
    SolverName,
)
from app.services.problem_service import ProblemContext


def _simulation() -> WalkForwardSimulation:
    points = (
        WalkForwardPoint(date(2025, 1, 30), 100_000.0, 0.0),
        WalkForwardPoint(date(2025, 1, 31), 101_000.0, 0.01),
        WalkForwardPoint(date(2025, 2, 3), 100_495.0, -0.005),
    )
    periods = (
        WalkForwardPeriod(
            1,
            date(2025, 1, 30),
            date(2025, 1, 31),
            date(2024, 1, 1),
            date(2025, 1, 29),
            252,
            {"A": 0.6, "B": 0.4},
            0.0,
            0.12,
            0.2,
        ),
        WalkForwardPeriod(
            2,
            date(2025, 2, 3),
            date(2025, 2, 3),
            date(2024, 2, 1),
            date(2025, 1, 31),
            252,
            {"A": 0.4, "B": 0.6},
            0.4,
            0.13,
            0.19,
        ),
    )
    return WalkForwardSimulation(
        ("A", "B"), RebalanceFrequency.MONTHLY, 252, points, periods, 0.4, ()
    )


def _problem_context() -> ProblemContext:
    problem = OptimizationInput(
        symbols=("A", "B"),
        expected_returns=np.asarray([0.1, 0.12]),
        covariance=np.diag([0.02, 0.03]),
        sectors=("One", "Two"),
        budget=100_000,
        risk_tolerance=1.0,
        max_single_weight=1.0,
        default_sector_cap=1.0,
        solver=SolverName.SCIPY,
    )
    return ProblemContext(
        problem, (), date(2025, 1, 29), (date(2024, 1, 1), date(2025, 1, 29))
    )


@pytest.mark.asyncio
async def test_service_persists_result_and_fetches_it_with_ownership(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = User(email="walk@example.com", password_hash="hash", full_name="Walk User")
    portfolio = Portfolio(user=user, name="Walk portfolio")
    run = OptimizationRun(
        portfolio=portfolio,
        solver_used="SciPy",
        budget=Decimal(100000),
        target_return=None,
        risk_tolerance=Decimal(1),
        max_single_weight=Decimal(1),
        min_holdings=1,
        sector_constraints={"default_sector_cap": 1.0, "risk_free_rate": 0.0},
        status="solved",
    )
    session.add_all([user, portfolio, run])
    await session.commit()

    async def fake_simulation(*_args, **_kwargs):
        return _simulation()

    async def fake_problem(*_args, **_kwargs):
        return _problem_context()

    async def fake_backtest(*_args, **_kwargs):
        return BacktestResult(
            BacktestMode.PERIODIC_REBALANCE,
            RebalanceFrequency.MONTHLY,
            ("A", "B"),
            (
                BacktestPoint(date(2025, 1, 30), 100_000, 0.0),
                BacktestPoint(date(2025, 1, 31), 100_500, 0.005),
                BacktestPoint(date(2025, 2, 3), 100_701, 0.002),
            ),
            (),
            "out_of_sample",
            date(2025, 1, 30),
        )

    solved = OptimizationResult(
        OptimizationStatus.OPTIMAL,
        SolverName.SCIPY,
        {"A": 0.5, "B": 0.5},
        0.0,
        0.11,
        0.025,
        0.158,
        1,
    )
    monkeypatch.setattr(
        "app.analytics.walk_forward_service.run_walk_forward_simulation",
        fake_simulation,
    )
    monkeypatch.setattr(
        "app.analytics.walk_forward_service.problem_from_run", fake_problem
    )
    monkeypatch.setattr(
        "app.analytics.walk_forward_service.run_backtest", fake_backtest
    )
    monkeypatch.setattr(
        "app.analytics.walk_forward_service.solve", lambda _problem: solved
    )

    payload = await run_walk_forward(
        session, user, Settings(), portfolio.id, date(2025, 1, 30), date(2025, 2, 3)
    )
    stored = await session.get(WalkForwardRun, payload.id)
    assert stored is not None
    assert stored.result["methodology"]["strict_pre_rebalance_estimation"] is True
    assert stored.result["methodology"]["transaction_costs_included"] is False
    fetched = await get_walk_forward_run(session, user, portfolio.id, stored.id)
    assert fetched.result == stored.result


@pytest.mark.asyncio
async def test_real_49_stock_walk_forward_matches_phase9c_period() -> None:
    database_url = os.getenv("REAL_DATABASE_URL")
    if not database_url:
        pytest.skip("set REAL_DATABASE_URL to run the 49-stock walk-forward comparison")
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            row = (
                await session.execute(
                    select(User, Portfolio)
                    .join(Portfolio, Portfolio.user_id == User.id)
                    .join(OptimizationRun, OptimizationRun.portfolio_id == Portfolio.id)
                    .where(OptimizationRun.status == "solved")
                    .order_by(OptimizationRun.run_at.desc())
                    .limit(1)
                )
            ).one_or_none()
            if row is None:
                pytest.skip("real database has no solved portfolio")
            user, portfolio = row
            payload = await run_walk_forward(
                session,
                user,
                Settings(database_url=database_url),
                portfolio.id,
                date(2025, 1, 30),
                date(2026, 1, 30),
                RebalanceFrequency.MONTHLY,
                252,
            )
            walk = payload.result["walk_forward"]["metrics"]
            static = payload.result["static_comparison"]["metrics"]
            print("walk-forward:", walk)
            print("static Phase 9C:", static)
            assert np.isfinite(list(walk.values())).all()
            assert len(payload.result["walk_forward"]["periods"]) == 13
            periods = payload.result["walk_forward"]["periods"]
            assert any(
                period["weights"] != periods[0]["weights"] for period in periods[1:]
            )
            assert payload.result["walk_forward"]["total_turnover"] > 0
            assert all(
                period["estimation_end_date"] < period["rebalance_date"]
                for period in payload.result["walk_forward"]["periods"]
            )
    finally:
        await engine.dispose()
