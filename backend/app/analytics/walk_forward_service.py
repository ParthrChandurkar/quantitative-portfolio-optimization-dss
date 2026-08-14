"""Persisted walk-forward orchestration and static out-of-sample comparison."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.backtest import BacktestMode, RebalanceFrequency, run_backtest
from app.analytics.risk_metrics import (
    historical_var_95,
    maximum_drawdown,
    realized_annualized_return,
    realized_annualized_volatility,
    sharpe_ratio,
)
from app.analytics.walk_forward import (
    WalkForwardSimulation,
    run_walk_forward_simulation,
)
from app.core.config import Settings
from app.core.errors import APIError
from app.db.models import OptimizationRun, StockPrice, User, WalkForwardRun
from app.optimization.engine import solve
from app.schemas.walk_forward import WalkForwardResult
from app.services.portfolio_service import require_owned_portfolio
from app.services.problem_service import decode_constraint_config, problem_from_run


def _realized_metrics(
    budget: float,
    returns,
    values,
    risk_free_rate: float,
) -> dict[str, float]:
    annual_return = realized_annualized_return(returns)
    annual_volatility = realized_annualized_volatility(returns)
    return {
        "annualized_return": annual_return,
        "annualized_volatility": annual_volatility,
        "sharpe_ratio": sharpe_ratio(annual_return, risk_free_rate, annual_volatility),
        "max_drawdown": maximum_drawdown(values),
        "historical_var_95_inr": historical_var_95(budget, returns),
        "final_value_inr": float(values[-1]),
    }


def _simulation_payload(simulation: WalkForwardSimulation) -> dict[str, Any]:
    return {
        "frequency": simulation.frequency.value,
        "lookback_days": simulation.lookback_days,
        "symbols": list(simulation.symbols),
        "points": [asdict(point) for point in simulation.points],
        "periods": [asdict(period) for period in simulation.periods],
        "total_turnover": simulation.total_turnover,
        "warnings": list(simulation.warnings),
    }


async def _latest_solved_run(
    session: AsyncSession, portfolio_id: uuid.UUID
) -> OptimizationRun:
    run = await session.scalar(
        select(OptimizationRun)
        .where(
            OptimizationRun.portfolio_id == portfolio_id,
            OptimizationRun.status == "solved",
        )
        .order_by(OptimizationRun.run_at.desc())
        .limit(1)
    )
    if run is None:
        raise ValueError("walk-forward requires a solved optimization run")
    return run


async def run_walk_forward(
    session: AsyncSession,
    user: User,
    settings: Settings,
    portfolio_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY,
    lookback_days: int = 252,
) -> WalkForwardResult:
    """Run, compare, persist, and return a chronological validation."""

    await require_owned_portfolio(session, portfolio_id, user.id)
    run = await _latest_solved_run(session, portfolio_id)
    selected_end = end_date or await session.scalar(
        select(func.max(StockPrice.trade_date))
    )
    if selected_end is None:
        raise ValueError("walk-forward requires loaded stock prices")
    selected_start = start_date or selected_end - timedelta(days=365)
    if selected_start >= selected_end:
        raise ValueError("start_date must precede end_date")

    simulation = await run_walk_forward_simulation(
        session,
        settings,
        run,
        selected_start,
        selected_end,
        rebalance_frequency,
        lookback_days,
    )
    config = decode_constraint_config(run.sector_constraints)
    risk_free_rate = float(config["risk_free_rate"])
    walk_metrics = _realized_metrics(
        float(run.budget),
        simulation.returns,
        simulation.values,
        risk_free_rate,
    )

    first_fit = await problem_from_run(
        session,
        settings,
        run,
        simulation.symbols,
        as_of_date=simulation.periods[0].rebalance_date - timedelta(days=1),
        lookback_days=lookback_days,
    )
    static_solve = await asyncio.to_thread(solve, first_fit.problem)
    if not static_solve.is_feasible:
        raise ValueError(f"static comparison solve failed: {static_solve.message}")
    static_result = await run_backtest(
        session,
        static_solve.weights,
        float(run.budget),
        selected_start,
        selected_end,
        BacktestMode.PERIODIC_REBALANCE,
        rebalance_frequency,
        estimation_end_date=simulation.periods[0].rebalance_date,
        estimation_dates=first_fit.estimation_dates,
    )
    static_metrics = _realized_metrics(
        float(run.budget),
        static_result.returns,
        static_result.values,
        risk_free_rate,
    )
    result_payload = jsonable_encoder(
        {
            "methodology": {
                "label": "WALK-FORWARD OUT-OF-SAMPLE BACKTEST",
                "strict_pre_rebalance_estimation": True,
                "transaction_costs_included": False,
                "start_date": selected_start,
                "end_date": selected_end,
            },
            "walk_forward": {
                **_simulation_payload(simulation),
                "metrics": walk_metrics,
            },
            "static_comparison": {
                "label": "STATIC SINGLE-SPLIT OUT-OF-SAMPLE",
                "points": [asdict(point) for point in static_result.points],
                "metrics": static_metrics,
            },
        }
    )
    constraints = {
        "budget_inr": float(run.budget),
        "target_return": float(run.target_return)
        if run.target_return is not None
        else None,
        "risk_tolerance": float(run.risk_tolerance)
        if run.risk_tolerance is not None
        else None,
        "max_single_weight": float(run.max_single_weight),
        **config,
    }
    stored = WalkForwardRun(
        portfolio_id=portfolio_id,
        rebalance_frequency=rebalance_frequency.value,
        lookback_days=lookback_days,
        start_date=selected_start,
        end_date=selected_end,
        constraints_snapshot=jsonable_encoder(constraints),
        result=result_payload,
    )
    session.add(stored)
    await session.commit()
    await session.refresh(stored)
    return WalkForwardResult(
        id=stored.id,
        portfolio_id=portfolio_id,
        rebalance_frequency=stored.rebalance_frequency,
        lookback_days=stored.lookback_days,
        start_date=stored.start_date,
        end_date=stored.end_date,
        constraints_snapshot=stored.constraints_snapshot,
        result=stored.result,
        created_at=stored.created_at,
    )


async def get_walk_forward_run(
    session: AsyncSession,
    user: User,
    portfolio_id: uuid.UUID,
    run_id: uuid.UUID,
) -> WalkForwardResult:
    await require_owned_portfolio(session, portfolio_id, user.id)
    stored = await session.get(WalkForwardRun, run_id)
    if stored is None or stored.portfolio_id != portfolio_id:
        raise APIError(403, "WALK_FORWARD_FORBIDDEN", "You do not own this run")
    return WalkForwardResult(
        id=stored.id,
        portfolio_id=stored.portfolio_id,
        rebalance_frequency=stored.rebalance_frequency,
        lookback_days=stored.lookback_days,
        start_date=stored.start_date,
        end_date=stored.end_date,
        constraints_snapshot=stored.constraints_snapshot,
        result=stored.result,
        created_at=stored.created_at,
    )
