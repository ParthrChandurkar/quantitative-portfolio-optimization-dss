"""Reconstruct stable optimization inputs from persisted runs and real market data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import OptimizationRun, Sector, Stock, StockPrice
from app.optimization.data import build_market_data
from app.optimization.types import OptimizationInput, SolverName


@dataclass(frozen=True, slots=True)
class ProblemContext:
    problem: OptimizationInput
    stocks: tuple[Stock, ...]
    as_of_date: date


def encode_constraint_config(
    sector_caps: dict[str, float],
    default_sector_cap: float,
    min_holdings: int | None,
    max_holdings: int | None,
    min_lot_weight: float,
    risk_free_rate: float,
) -> dict[str, Any]:
    return {
        "caps": dict(sector_caps),
        "default_sector_cap": default_sector_cap,
        "min_holdings": min_holdings,
        "max_holdings": max_holdings,
        "min_lot_weight": min_lot_weight,
        "risk_free_rate": risk_free_rate,
    }


def decode_constraint_config(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("caps"), dict):
        return {
            "caps": {str(key): float(value) for key, value in payload["caps"].items()},
            "default_sector_cap": float(payload.get("default_sector_cap", 0.35)),
            "min_holdings": payload.get("min_holdings"),
            "max_holdings": payload.get("max_holdings"),
            "min_lot_weight": float(payload.get("min_lot_weight", 0.01)),
            "risk_free_rate": float(payload.get("risk_free_rate", 0.0)),
        }
    return {
        "caps": {str(key): float(value) for key, value in payload.items()},
        "default_sector_cap": 0.35,
        "min_holdings": None,
        "max_holdings": None,
        "min_lot_weight": 0.01,
        "risk_free_rate": 0.0,
    }


async def latest_market_date(
    session: AsyncSession, stock_ids: tuple
) -> date:
    value = await session.scalar(
        select(func.max(StockPrice.trade_date)).where(StockPrice.stock_id.in_(stock_ids))
    )
    if value is None:
        raise ValueError("selected stocks have no market data")
    return value


async def stock_universe(
    session: AsyncSession, symbols: tuple[str, ...] | None = None
) -> tuple[tuple[Stock, ...], tuple[str, ...]]:
    statement = (
        select(Stock, Sector.name)
        .join(Sector, Stock.sector_id == Sector.id)
        .order_by(Stock.symbol)
    )
    if symbols is not None:
        statement = statement.where(Stock.symbol.in_(symbols))
    rows = (await session.execute(statement)).all()
    by_symbol = {stock.symbol: (stock, sector) for stock, sector in rows}
    ordered_symbols = symbols or tuple(sorted(by_symbol))
    if any(symbol not in by_symbol for symbol in ordered_symbols):
        raise ValueError("one or more requested stocks are missing")
    return (
        tuple(by_symbol[symbol][0] for symbol in ordered_symbols),
        tuple(by_symbol[symbol][1] for symbol in ordered_symbols),
    )


async def build_problem(
    session: AsyncSession,
    settings: Settings,
    *,
    symbols: tuple[str, ...] | None,
    budget: float,
    target_return: float | None,
    risk_tolerance: float | None,
    max_single_weight: float,
    sector_caps: dict[str, float],
    default_sector_cap: float,
    min_holdings: int | None,
    max_holdings: int | None,
    min_lot_weight: float,
    risk_free_rate: float,
    solver: SolverName,
    lookback_days: int | None = None,
) -> ProblemContext:
    stocks, sectors = await stock_universe(session, symbols)
    if len(stocks) < 2:
        raise ValueError("optimization requires at least two stocks")
    selected_symbols = tuple(stock.symbol for stock in stocks)
    as_of_date = await latest_market_date(session, tuple(stock.id for stock in stocks))
    market = await build_market_data(
        session,
        selected_symbols,
        as_of_date,
        lookback_days or settings.covariance_lookback_days,
    )
    problem = OptimizationInput(
        symbols=selected_symbols,
        expected_returns=market.expected_returns,
        covariance=market.covariance,
        sectors=sectors,
        budget=budget,
        target_return=target_return,
        risk_tolerance=risk_tolerance,
        max_single_weight=max_single_weight,
        sector_caps=sector_caps,
        default_sector_cap=default_sector_cap,
        min_holdings=min_holdings,
        max_holdings=max_holdings,
        min_lot_weight=min_lot_weight,
        historical_returns=market.historical_returns,
        solver=solver,
        risk_free_rate=risk_free_rate,
    )
    return ProblemContext(problem, stocks, as_of_date)


async def problem_from_run(
    session: AsyncSession,
    settings: Settings,
    run: OptimizationRun,
    symbols: tuple[str, ...],
) -> ProblemContext:
    config = decode_constraint_config(run.sector_constraints)
    try:
        solver = SolverName(run.solver_used)
    except ValueError:
        solver = SolverName.AUTO
    return await build_problem(
        session,
        settings,
        symbols=symbols,
        budget=float(run.budget),
        target_return=float(run.target_return) if run.target_return is not None else None,
        risk_tolerance=float(run.risk_tolerance)
        if run.risk_tolerance is not None
        else None,
        max_single_weight=float(run.max_single_weight),
        sector_caps=config["caps"],
        default_sector_cap=config["default_sector_cap"],
        min_holdings=config["min_holdings"],
        max_holdings=config["max_holdings"],
        min_lot_weight=config["min_lot_weight"],
        risk_free_rate=config["risk_free_rate"],
        solver=solver,
    )
