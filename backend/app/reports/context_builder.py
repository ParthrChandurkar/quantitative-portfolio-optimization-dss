"""Assemble report data exclusively from existing persisted and service outputs."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.backtest import default_out_of_sample_split
from app.analytics.service import (
    AnalyticsBundle,
    AnalyticsDateRange,
    SnapshotAnalyticsInput,
    get_analytics,
)
from app.core.config import get_settings
from app.db.models import (
    ConstraintLog,
    OptimizationRun,
    Portfolio,
    PortfolioHolding,
    PortfolioSnapshot,
    Sector,
    Stock,
    StockPrice,
    User,
)
from app.db.models import ExplanationItem as StoredExplanationItem
from app.explainability.portfolio_summary import build_portfolio_summary
from app.explainability.shadow_price_insights import (
    ShadowPriceInsight,
    build_shadow_price_insights,
)
from app.optimization.engine import solve
from app.optimization.types import ConstraintReport
from app.services.problem_service import decode_constraint_config, problem_from_run


@dataclass(frozen=True, slots=True)
class ReportMetrics:
    expected_return: Decimal | None
    expected_volatility: Decimal | None
    sharpe_ratio: Decimal | None
    diversification_score: Decimal | None


@dataclass(frozen=True, slots=True)
class ReportHolding:
    symbol: str
    company_name: str
    sector: str
    weight: Decimal
    allocated_amount_inr: Decimal
    shares: Decimal


@dataclass(frozen=True, slots=True)
class ConfiguredConstraints:
    budget_inr: Decimal
    target_return: Decimal | None
    risk_tolerance: Decimal | None
    max_single_weight: Decimal
    min_holdings: int
    sector_caps: dict[str, float]


@dataclass(frozen=True, slots=True)
class ReportConstraint:
    constraint_name: str
    is_binding: bool
    slack_value: Decimal | None
    shadow_price: Decimal | None


@dataclass(frozen=True, slots=True)
class ReportExplanation:
    symbol: str | None
    decision: str
    primary_reason: str
    marginal_return_contribution: Decimal | None
    marginal_risk_contribution: Decimal | None
    binding_constraint: str | None
    narrative_text: str


@dataclass(frozen=True, slots=True)
class ReportContext:
    generated_at: datetime
    portfolio_name: str
    snapshot_label: str
    investor_name: str
    metrics: ReportMetrics
    holdings: tuple[ReportHolding, ...]
    plain_language_summary: str
    model_formulation: str
    solver_used: str
    solve_time_ms: int | None
    configured_constraints: ConfiguredConstraints
    constraint_rows: tuple[ReportConstraint, ...]
    explanations: tuple[ReportExplanation, ...]
    notable_exclusions: tuple[ReportExplanation, ...]
    shadow_price_insights: tuple[ShadowPriceInsight, ...]
    analytics: AnalyticsBundle


def model_formulation(solver_used: str) -> str:
    normalized = solver_used.casefold()
    if "pulp" in normalized or "milp" in normalized:
        return "Mixed-Integer Linear Programming (MILP) — Konno-Yamazaki MAD"
    if "or-tools" in normalized or "ortools" in normalized:
        return "Hybrid CP-SAT support selection with continuous QP refinement"
    return "Continuous quadratic programming (mean-variance QP)"


def assemble_report_context(
    snapshot: PortfolioSnapshot,
    portfolio: Portfolio,
    investor: User,
    run: OptimizationRun,
    holding_rows: tuple[tuple[PortfolioHolding, Stock, Sector], ...],
    explanation_rows: tuple[tuple[StoredExplanationItem, str | None], ...],
    constraint_logs: tuple[ConstraintLog, ...],
    analytics: AnalyticsBundle,
    *,
    generated_at: datetime | None = None,
) -> ReportContext:
    """Format existing values without introducing a second calculation path."""

    holdings = tuple(
        ReportHolding(
            symbol=stock.symbol,
            company_name=stock.company_name,
            sector=sector.name,
            weight=holding.weight,
            allocated_amount_inr=holding.allocated_amount,
            shares=holding.shares,
        )
        for holding, stock, sector in holding_rows
    )
    explanations = tuple(
        ReportExplanation(
            symbol=symbol,
            decision=item.decision,
            primary_reason=item.primary_reason,
            marginal_return_contribution=item.marginal_return_contribution,
            marginal_risk_contribution=item.marginal_risk_contribution,
            binding_constraint=item.binding_constraint,
            narrative_text=item.narrative_text,
        )
        for item, symbol in explanation_rows
    )
    constraints = tuple(
        ReportConstraint(
            constraint_name=item.constraint_name,
            is_binding=item.is_binding,
            slack_value=item.slack_value,
            shadow_price=item.shadow_price,
        )
        for item in constraint_logs
    )
    phase4_reports = tuple(
        ConstraintReport(
            constraint_name=item.constraint_name,
            is_satisfied=True,
            is_binding=item.is_binding,
            slack_value=float(item.slack_value) if item.slack_value is not None else None,
            shadow_price=float(item.shadow_price) if item.shadow_price is not None else None,
        )
        for item in constraint_logs
    )
    if snapshot.expected_return is None or snapshot.expected_volatility is None:
        raise ValueError("report snapshot is missing expected return or volatility")
    constraint_config = decode_constraint_config(run.sector_constraints)
    weights = {holding.symbol: float(holding.weight) for holding in holdings}
    sectors = {holding.symbol: holding.sector for holding in holdings}
    return ReportContext(
        generated_at=generated_at or datetime.now(UTC),
        portfolio_name=portfolio.name,
        snapshot_label=snapshot.label,
        investor_name=investor.full_name,
        metrics=ReportMetrics(
            expected_return=snapshot.expected_return,
            expected_volatility=snapshot.expected_volatility,
            sharpe_ratio=snapshot.sharpe_ratio,
            diversification_score=snapshot.diversification_score,
        ),
        holdings=holdings,
        plain_language_summary=build_portfolio_summary(
            float(snapshot.expected_return),
            float(snapshot.expected_volatility),
            weights,
            sectors,
        ),
        model_formulation=model_formulation(run.solver_used),
        solver_used=run.solver_used,
        solve_time_ms=run.solve_time_ms,
        configured_constraints=ConfiguredConstraints(
            budget_inr=run.budget,
            target_return=run.target_return,
            risk_tolerance=run.risk_tolerance,
            max_single_weight=run.max_single_weight,
            min_holdings=run.min_holdings,
            sector_caps=constraint_config["caps"],
        ),
        constraint_rows=constraints,
        explanations=explanations,
        notable_exclusions=tuple(
            item for item in explanations if item.decision.casefold() == "excluded"
        ),
        shadow_price_insights=build_shadow_price_insights(phase4_reports),
        analytics=analytics,
    )


async def load_report_context(
    session: AsyncSession,
    snapshot_id: uuid.UUID,
    user_id: uuid.UUID,
    date_range: AnalyticsDateRange | None = None,
) -> ReportContext:
    """Load an owned snapshot and reuse the Phase 7 service for analytics values."""

    root = (
        await session.execute(
            select(PortfolioSnapshot, OptimizationRun, Portfolio, User)
            .join(OptimizationRun, PortfolioSnapshot.optimization_run_id == OptimizationRun.id)
            .join(Portfolio, PortfolioSnapshot.portfolio_id == Portfolio.id)
            .join(User, Portfolio.user_id == User.id)
            .where(PortfolioSnapshot.id == snapshot_id, User.id == user_id)
        )
    ).one_or_none()
    if root is None:
        raise LookupError("snapshot was not found for this user")
    snapshot, run, portfolio, investor = root
    holding_result = await session.execute(
        select(PortfolioHolding, Stock, Sector)
        .join(Stock, PortfolioHolding.stock_id == Stock.id)
        .join(Sector, Stock.sector_id == Sector.id)
        .where(PortfolioHolding.snapshot_id == snapshot.id)
        .order_by(PortfolioHolding.weight.desc(), Stock.symbol)
    )
    holding_rows = tuple(
        (holding, stock, sector) for holding, stock, sector in holding_result.all()
    )
    if not holding_rows:
        raise ValueError("report snapshot has no holdings")
    explanation_result = await session.execute(
        select(StoredExplanationItem, Stock.symbol)
        .outerjoin(Stock, StoredExplanationItem.stock_id == Stock.id)
        .where(StoredExplanationItem.optimization_run_id == run.id)
        .order_by(Stock.symbol)
    )
    explanation_rows = tuple(
        (item, symbol) for item, symbol in explanation_result.all()
    )
    constraint_logs = tuple(
        (
            await session.scalars(
                select(ConstraintLog)
                .where(ConstraintLog.optimization_run_id == run.id)
                .order_by(ConstraintLog.constraint_name)
            )
        ).all()
    )
    stock_ids = tuple(stock.id for _, stock, _ in holding_rows)
    as_of_date = await session.scalar(
        select(func.max(StockPrice.trade_date)).where(StockPrice.stock_id.in_(stock_ids))
    )
    if as_of_date is None:
        raise ValueError("report holdings have no historical prices")
    selected_range = date_range or AnalyticsDateRange(
        await default_out_of_sample_split(session, as_of_date), as_of_date
    )
    split_date = selected_range.start_date
    fit_context = await problem_from_run(
        session,
        get_settings(),
        run,
        None,
        as_of_date=split_date - timedelta(days=1),
    )
    fitted_result = await asyncio.to_thread(solve, fit_context.problem)
    if not fitted_result.is_feasible:
        raise ValueError(f"out-of-sample report fit failed: {fitted_result.message}")
    analytics = await get_analytics(
        SnapshotAnalyticsInput(
            fitted_result.weights,
            fitted_result.constraint_reports,
        ),
        fit_context.problem,
        selected_range,
        session=session,
        estimation_end_date=split_date,
        estimation_dates=fit_context.estimation_dates,
    )
    return assemble_report_context(
        snapshot,
        portfolio,
        investor,
        run,
        holding_rows,
        explanation_rows,
        constraint_logs,
        analytics,
    )
