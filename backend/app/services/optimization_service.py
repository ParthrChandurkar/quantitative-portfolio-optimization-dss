"""Persisted Phase 4 solve plus Phase 5 explanations in one workflow."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.service import check_alerts
from app.analytics.risk_metrics import sharpe_ratio
from app.core.config import Settings
from app.core.errors import APIError
from app.db.models import (
    ConstraintLog,
    OptimizationRun,
    PortfolioHolding,
    PortfolioSnapshot,
    StockPrice,
    User,
)
from app.db.models import ExplanationItem as StoredExplanationItem
from app.explainability.service import ExplainabilityBundle, build_explanations
from app.optimization.engine import solve
from app.optimization.types import OptimizationResult, OptimizationStatus
from app.schemas.optimization import OptimizeRequest
from app.services.portfolio_service import require_owned_portfolio, snapshot_payload
from app.services.problem_service import build_problem, encode_constraint_config


def _run_payload(run: OptimizationRun, message: str | None = None) -> dict:
    return {
        "id": run.id,
        "portfolio_id": run.portfolio_id,
        "status": run.status,
        "solver_used": run.solver_used,
        "solve_time_ms": run.solve_time_ms,
        "return_estimation_method": run.return_estimation_method,
        "message": message,
    }


def _explanation_payload(bundle: ExplainabilityBundle) -> dict:
    def item_payload(item) -> dict:
        return {
            "symbol": item.symbol,
            "decision": item.decision,
            "primary_reason": item.primary_reason.value,
            "marginal_return_contribution": item.marginal_return_contribution,
            "marginal_risk_contribution": item.marginal_risk_contribution,
            "binding_constraint": item.binding_constraint,
            "narrative_text": item.narrative_text,
            "rationale": item.rationale,
            "model_score": item.model_score,
        }

    return {
        "summary": bundle.summary,
        "included": [item_payload(item) for item in bundle.included],
        "notable_exclusions": [
            item_payload(item) for item in bundle.notable_exclusions
        ],
        "constraint_insights": [
            {
                "constraint_name": item.constraint_name,
                "shadow_price": item.shadow_price,
                "assumed_relaxation": item.assumed_relaxation,
                "projected_objective_change": item.projected_objective_change,
                "narrative": item.narrative,
            }
            for item in bundle.constraint_insights
        ],
        "diversification": {
            "overall_score": bundle.diversification.overall_score,
            "stock_concentration_hhi": bundle.diversification.stock_concentration_hhi,
            "sector_concentration_hhi": bundle.diversification.sector_concentration_hhi,
        },
    }


async def _latest_prices(
    session: AsyncSession, stock_ids: tuple[uuid.UUID, ...]
) -> dict[uuid.UUID, Decimal]:
    maxima = (
        select(
            StockPrice.stock_id,
            func.max(StockPrice.trade_date).label("latest_date"),
        )
        .where(StockPrice.stock_id.in_(stock_ids))
        .group_by(StockPrice.stock_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(StockPrice.stock_id, StockPrice.adj_close).join(
                maxima,
                (StockPrice.stock_id == maxima.c.stock_id)
                & (StockPrice.trade_date == maxima.c.latest_date),
            )
        )
    ).all()
    return {stock_id: price for stock_id, price in rows}


async def _persist_solution(
    session: AsyncSession,
    run: OptimizationRun,
    request: OptimizeRequest,
    result: OptimizationResult,
    explanations: ExplainabilityBundle,
    stocks,
) -> tuple[PortfolioSnapshot, list[dict]]:
    assert result.expected_return is not None
    assert result.expected_volatility is not None
    prices = await _latest_prices(session, tuple(stock.id for stock in stocks))
    stock_by_symbol = {stock.symbol: stock for stock in stocks}
    baseline_count = await session.scalar(
        select(func.count())
        .select_from(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == run.portfolio_id)
    )
    snapshot = PortfolioSnapshot(
        portfolio_id=run.portfolio_id,
        optimization_run_id=run.id,
        label=request.label,
        expected_return=Decimal(str(result.expected_return)),
        expected_volatility=Decimal(str(result.expected_volatility)),
        sharpe_ratio=Decimal(
            str(
                sharpe_ratio(
                    result.expected_return,
                    request.risk_free_rate,
                    result.expected_volatility,
                )
            )
        ),
        diversification_score=Decimal(str(explanations.diversification.overall_score)),
        is_baseline=(baseline_count or 0) == 0,
    )
    session.add(snapshot)
    await session.flush()
    holding_payloads: list[dict] = []
    for symbol, weight in result.weights.items():
        if weight <= 1e-8:
            continue
        stock = stock_by_symbol[symbol]
        allocation = Decimal(str(request.budget * weight))
        price = prices.get(stock.id)
        shares = allocation / price if price is not None and price > 0 else Decimal(0)
        session.add(
            PortfolioHolding(
                snapshot_id=snapshot.id,
                stock_id=stock.id,
                weight=Decimal(str(weight)),
                allocated_amount=allocation,
                shares=shares,
            )
        )
        holding_payloads.append(
            {
                "symbol": symbol,
                "company_name": stock.company_name,
                "weight": weight,
                "allocated_amount_inr": float(allocation),
                "shares": float(shares),
            }
        )
    for item in (*explanations.included, *explanations.notable_exclusions):
        stock = stock_by_symbol.get(item.symbol)
        session.add(
            StoredExplanationItem(
                optimization_run_id=run.id,
                stock_id=stock.id if stock is not None else None,
                decision=item.decision,
                primary_reason=item.primary_reason.value,
                marginal_return_contribution=Decimal(
                    str(item.marginal_return_contribution)
                ),
                marginal_risk_contribution=Decimal(str(item.marginal_risk_contribution)),
                binding_constraint=item.binding_constraint,
                narrative_text=item.narrative_text,
            )
        )
    for report in result.constraint_reports:
        session.add(
            ConstraintLog(
                optimization_run_id=run.id,
                constraint_name=report.constraint_name,
                is_binding=report.is_binding,
                slack_value=Decimal(str(report.slack_value))
                if report.slack_value is not None
                else None,
                shadow_price=Decimal(str(report.shadow_price))
                if report.shadow_price is not None
                else None,
            )
        )
    return snapshot, holding_payloads


async def optimize_portfolio(
    session: AsyncSession,
    user: User,
    portfolio_id: uuid.UUID,
    request: OptimizeRequest,
    settings: Settings,
) -> dict:
    await require_owned_portfolio(session, portfolio_id, user.id)
    context = await build_problem(
        session,
        settings,
        symbols=None,
        budget=request.budget,
        target_return=request.target_return,
        risk_tolerance=request.risk_tolerance,
        max_single_weight=request.max_single_weight,
        sector_caps=request.sector_caps,
        default_sector_cap=request.default_sector_cap,
        min_holdings=request.min_holdings,
        max_holdings=request.max_holdings,
        min_lot_weight=request.min_lot_weight,
        risk_free_rate=request.risk_free_rate,
        solver=request.solver,
        lookback_days=request.lookback_days,
        return_estimation_method=request.return_estimation_method,
    )
    run = OptimizationRun(
        portfolio_id=portfolio_id,
        solver_used=request.solver.value,
        budget=Decimal(str(request.budget)),
        target_return=Decimal(str(request.target_return))
        if request.target_return is not None
        else None,
        risk_tolerance=Decimal(str(request.risk_tolerance))
        if request.risk_tolerance is not None
        else None,
        max_single_weight=Decimal(str(request.max_single_weight)),
        min_holdings=request.min_holdings or 1,
        sector_constraints=encode_constraint_config(
            request.sector_caps,
            request.default_sector_cap,
            request.min_holdings,
            request.max_holdings,
            request.min_lot_weight,
            request.risk_free_rate,
        ),
        status="pending",
        return_estimation_method=request.return_estimation_method,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    result = await asyncio.to_thread(solve, context.problem)
    run.solver_used = result.solver_used.value
    run.solve_time_ms = result.solve_time_ms
    if result.status is OptimizationStatus.INFEASIBLE:
        run.status = "infeasible"
        await session.commit()
        return {"run": _run_payload(run, result.message), "snapshot": None, "explanations": None}
    if not result.is_feasible:
        run.status = "failed"
        await session.commit()
        return {"run": _run_payload(run, result.message), "snapshot": None, "explanations": None}
    explanations = build_explanations(result)
    snapshot, holdings = await _persist_solution(
        session, run, request, result, explanations, context.stocks
    )
    run.status = "solved"
    await session.commit()
    await session.refresh(snapshot)
    await check_alerts(session, user.id, portfolio_id)
    return {
        "run": _run_payload(run, result.message),
        "snapshot": {**snapshot_payload(snapshot), "holdings": holdings},
        "explanations": _explanation_payload(explanations),
    }


async def get_optimization_run(
    session: AsyncSession, user: User, run_id: uuid.UUID
) -> dict:
    run = await session.get(OptimizationRun, run_id)
    if run is None:
        raise APIError(403, "RUN_FORBIDDEN", "You do not own this optimization run")
    await require_owned_portfolio(session, run.portfolio_id, user.id)
    return _run_payload(run)
