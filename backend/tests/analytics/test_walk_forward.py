from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np
import pytest

from app.analytics.backtest import RebalanceFrequency, ReturnPanel
from app.analytics.walk_forward import (
    RebalanceDecision,
    assert_pre_rebalance_estimation,
    optimize_rebalance_period,
    run_walk_forward_simulation,
    walk_forward_rebalance_dates,
)
from app.core.config import Settings
from app.db.models import OptimizationRun
from app.optimization.types import (
    OptimizationInput,
    OptimizationResult,
    OptimizationStatus,
    SolverName,
)
from app.services.problem_service import ProblemContext


def _context(estimation_dates: tuple[date, ...]) -> ProblemContext:
    problem = OptimizationInput(
        symbols=("BANK", "IT", "ENERGY"),
        expected_returns=np.asarray([0.10, 0.12, 0.14]),
        covariance=np.diag([0.02, 0.03, 0.04]),
        sectors=("Financials", "Technology", "Energy"),
        budget=100_000,
        risk_tolerance=1.0,
        max_single_weight=1.0,
        default_sector_cap=1.0,
        solver=SolverName.SCIPY,
    )
    return ProblemContext(problem, (), estimation_dates[-1], estimation_dates)


def _run() -> OptimizationRun:
    return OptimizationRun(
        portfolio_id=None,  # type: ignore[arg-type]
        solver_used="SciPy",
        budget=Decimal(100000),
        target_return=None,
        risk_tolerance=Decimal(1),
        max_single_weight=Decimal(1),
        min_holdings=1,
        sector_constraints={},
        status="solved",
    )


def test_each_period_rejects_a_fit_date_on_its_rebalance_date() -> None:
    for rebalance in (date(2025, 1, 2), date(2025, 2, 3), date(2025, 3, 3)):
        with pytest.raises(ValueError, match="strictly before"):
            assert_pre_rebalance_estimation((date(2024, 12, 31), rebalance), rebalance)

    with pytest.raises(ValueError, match="dated observations"):
        assert_pre_rebalance_estimation((), date(2025, 1, 2))
    with pytest.raises(ValueError, match="at least one market date"):
        walk_forward_rebalance_dates((), RebalanceFrequency.MONTHLY)


@pytest.mark.asyncio
async def test_single_period_step_rebuilds_problem_and_measures_turnover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context((date(2024, 12, 30), date(2024, 12, 31)))
    captured = {}

    async def fake_problem(*_args, **kwargs):
        captured.update(kwargs)
        return context

    solved = OptimizationResult(
        OptimizationStatus.OPTIMAL,
        SolverName.SCIPY,
        {"BANK": 0.2, "IT": 0.3, "ENERGY": 0.5},
        0.0,
        0.13,
        0.04,
        0.2,
        1,
    )
    monkeypatch.setattr("app.analytics.walk_forward.problem_from_run", fake_problem)
    monkeypatch.setattr("app.analytics.walk_forward.solve", lambda _problem: solved)
    decision = await optimize_rebalance_period(
        None,  # type: ignore[arg-type]
        Settings(),
        _run(),
        context.problem.symbols,
        date(2025, 1, 2),
        252,
        {"BANK": 0.4, "IT": 0.3, "ENERGY": 0.3},
    )
    assert captured["as_of_date"] == date(2025, 1, 1)
    assert captured["lookback_days"] == 252
    assert decision.turnover == pytest.approx(0.4)
    assert decision.expected_return == 0.13


@pytest.mark.asyncio
async def test_single_period_step_rejects_solver_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context((date(2024, 12, 30), date(2024, 12, 31)))

    async def fake_problem(*_args, **_kwargs):
        return context

    failed = OptimizationResult(
        OptimizationStatus.INFEASIBLE,
        SolverName.SCIPY,
        {},
        None,
        None,
        None,
        None,
        1,
        message="fixture infeasible",
    )
    monkeypatch.setattr("app.analytics.walk_forward.problem_from_run", fake_problem)
    monkeypatch.setattr("app.analytics.walk_forward.solve", lambda _problem: failed)
    with pytest.raises(ValueError, match="fixture infeasible"):
        await optimize_rebalance_period(
            None,  # type: ignore[arg-type]
            Settings(),
            _run(),
            context.problem.symbols,
            date(2025, 1, 2),
            252,
        )


@pytest.mark.asyncio
async def test_multi_period_simulation_enforces_invariant_and_changes_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_dates = (
        date(2025, 1, 2),
        date(2025, 1, 3),
        date(2025, 2, 3),
        date(2025, 2, 4),
        date(2025, 3, 3),
        date(2025, 3, 4),
    )
    panel = ReturnPanel(
        market_dates,
        np.asarray(
            [
                [0.0, 0.0, 0.0],
                [0.01, -0.01, 0.0],
                [-0.01, 0.02, 0.0],
                [0.0, 0.01, -0.01],
                [0.0, -0.01, 0.02],
                [0.01, 0.0, 0.01],
            ]
        ),
        np.ones((6, 3), dtype=bool),
        (),
    )
    weights = (
        {"BANK": 0.7, "IT": 0.2, "ENERGY": 0.1},
        {"BANK": 0.2, "IT": 0.7, "ENERGY": 0.1},
        {"BANK": 0.1, "IT": 0.2, "ENERGY": 0.7},
    )
    fit_dates = (
        (date(2024, 12, 27), date(2024, 12, 31)),
        (date(2025, 1, 30), date(2025, 1, 31)),
        (date(2025, 2, 27), date(2025, 2, 28)),
    )
    calls = 0

    async def fake_universe(_session):
        stocks = tuple(type("Stock", (), {"symbol": symbol})() for symbol in weights[0])
        return stocks, ("Financials", "Technology", "Energy")

    async def fake_panel(*_args, **_kwargs):
        return panel

    async def fake_period(*_args, **_kwargs):
        nonlocal calls
        index = calls
        calls += 1
        return RebalanceDecision(
            _context(fit_dates[index]),
            weights[index],
            0.0 if index == 0 else 1.0,
            0.12,
            0.2,
        )

    monkeypatch.setattr("app.analytics.walk_forward.stock_universe", fake_universe)
    monkeypatch.setattr("app.analytics.walk_forward.fetch_return_panel", fake_panel)
    monkeypatch.setattr(
        "app.analytics.walk_forward.optimize_rebalance_period", fake_period
    )
    result = await run_walk_forward_simulation(
        None,  # type: ignore[arg-type]
        Settings(),
        _run(),
        market_dates[0],
        market_dates[-1],
        RebalanceFrequency.MONTHLY,
        20,
    )

    assert len(result.periods) == 3
    assert result.periods[0].weights != result.periods[1].weights
    assert result.periods[1].weights != result.periods[2].weights
    assert all(
        period.estimation_end_date < period.rebalance_date for period in result.periods
    )
    assert result.total_turnover == pytest.approx(2.0)
    assert len(result.points) == len(market_dates)


@pytest.mark.asyncio
async def test_simulation_rechecks_invariant_even_if_period_step_is_faulty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rebalance = date(2025, 1, 2)
    panel = ReturnPanel((rebalance,), np.zeros((1, 3)), np.ones((1, 3), dtype=bool), ())

    async def fake_universe(_session):
        stocks = tuple(
            type("Stock", (), {"symbol": value})() for value in ("BANK", "IT", "ENERGY")
        )
        return stocks, ("Financials", "Technology", "Energy")

    async def fake_panel(*_args, **_kwargs):
        return panel

    async def faulty_period(*_args, **_kwargs):
        return RebalanceDecision(
            _context((date(2024, 12, 31), rebalance)),
            {"BANK": 0.4, "IT": 0.3, "ENERGY": 0.3},
            0.0,
            0.12,
            0.2,
        )

    monkeypatch.setattr("app.analytics.walk_forward.stock_universe", fake_universe)
    monkeypatch.setattr("app.analytics.walk_forward.fetch_return_panel", fake_panel)
    monkeypatch.setattr(
        "app.analytics.walk_forward.optimize_rebalance_period", faulty_period
    )
    with pytest.raises(ValueError, match="look-ahead detected"):
        await run_walk_forward_simulation(
            None,  # type: ignore[arg-type]
            Settings(),
            _run(),
            rebalance,
            rebalance,
            RebalanceFrequency.MONTHLY,
            20,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start", "end", "lookback", "message"),
    [
        (date(2025, 1, 3), date(2025, 1, 2), 20, "end_date"),
        (date(2025, 1, 2), date(2025, 1, 3), 1, "lookback_days"),
    ],
)
async def test_simulation_validates_range_before_querying(
    start: date, end: date, lookback: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        await run_walk_forward_simulation(
            None,  # type: ignore[arg-type]
            Settings(),
            _run(),
            start,
            end,
            RebalanceFrequency.MONTHLY,
            lookback,
        )
