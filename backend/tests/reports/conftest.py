from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.analytics.backtest import BacktestMode, BacktestPoint, BacktestResult
from app.analytics.efficient_frontier import FrontierPoint
from app.analytics.growth_projection import GrowthPoint
from app.analytics.risk_metrics import RiskMetrics
from app.analytics.sector_distribution import SectorAllocation
from app.analytics.service import (
    AllocationPoint,
    AnalyticsBundle,
    MethodologyAudit,
    PerformanceAnalytics,
    RiskReturnPoint,
)
from app.db.models import (
    ConstraintLog,
    ExplanationItem,
    OptimizationRun,
    Portfolio,
    PortfolioHolding,
    PortfolioSnapshot,
    Sector,
    Stock,
    User,
)
from app.optimization.types import ConstraintReport
from app.reports.context_builder import ReportContext, assemble_report_context


@pytest.fixture
def analytics_bundle() -> AnalyticsBundle:
    dates = (date(2025, 1, 2), date(2025, 1, 3))
    backtest = BacktestResult(
        BacktestMode.BUY_AND_HOLD,
        None,
        ("ALPHA", "BETA"),
        (
            BacktestPoint(dates[0], 100_000.0, 0.0),
            BacktestPoint(dates[1], 101_000.0, 0.01),
        ),
        (),
    )
    report = ConstraintReport("C4 Sector cap: IT", True, True, 0.0, 0.02)
    return AnalyticsBundle(
        methodology=MethodologyAudit(
            "OUT-OF-SAMPLE BACKTEST",
            date(2024, 1, 2),
            date(2025, 1, 1),
            date(2025, 1, 2),
            date(2025, 1, 2),
            date(2025, 1, 3),
            252,
            2,
            False,
        ),
        allocation=(
            AllocationPoint("ALPHA", "IT", 0.60, 60_000.0),
            AllocationPoint("BETA", "Energy", 0.40, 40_000.0),
        ),
        risk_return=RiskReturnPoint(0.14, 0.18),
        growth_projection=(
            GrowthPoint(0, 100_000.0, 100_000.0, 100_000.0, 100_000.0, 100_000.0),
        ),
        performance=PerformanceAnalytics(backtest, backtest),
        risk_metrics=RiskMetrics(0.67, 0.18, 0.16, -0.10, 15_610.0, 4_000.0),
        efficient_frontier=(
            FrontierPoint(0.14, 0.14, 0.18, {"ALPHA": 0.6, "BETA": 0.4}, (report,)),
        ),
        sector_distribution=(
            SectorAllocation("Energy", 0.40, 0.50, 0.10, False, False),
            SectorAllocation("IT", 0.60, 0.60, 0.0, True, False),
        ),
    )


@pytest.fixture
def report_context(analytics_bundle: AnalyticsBundle) -> ReportContext:
    user_id, portfolio_id, run_id, snapshot_id = (uuid.uuid4() for _ in range(4))
    user = User(
        id=user_id,
        email="investor@example.com",
        password_hash="hash",
        full_name="Test Investor",
    )
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=user_id,
        name="Balanced Nifty Portfolio",
        is_active=True,
    )
    run = OptimizationRun(
        id=run_id,
        portfolio_id=portfolio_id,
        solver_used="SciPy",
        budget=Decimal("100000.00"),
        target_return=Decimal("0.1400000000"),
        risk_tolerance=Decimal("0.2000000000"),
        max_single_weight=Decimal("0.6000000000"),
        min_holdings=2,
        sector_constraints={"IT": 0.60, "Energy": 0.50},
        status="OPTIMAL",
        solve_time_ms=42,
    )
    snapshot = PortfolioSnapshot(
        id=snapshot_id,
        portfolio_id=portfolio_id,
        optimization_run_id=run_id,
        label="Baseline recommendation",
        expected_return=Decimal("0.1400000000"),
        expected_volatility=Decimal("0.1800000000"),
        sharpe_ratio=Decimal("0.6666666667"),
        diversification_score=Decimal("82.5000000000"),
        is_baseline=True,
    )
    it = Sector(id=uuid.uuid4(), name="IT")
    energy = Sector(id=uuid.uuid4(), name="Energy")
    alpha = Stock(
        id=uuid.uuid4(), symbol="ALPHA", company_name="Alpha Ltd", sector=it
    )
    beta = Stock(
        id=uuid.uuid4(), symbol="BETA", company_name="Beta Ltd", sector=energy
    )
    holdings = (
        (
            PortfolioHolding(
                snapshot_id=snapshot_id,
                stock_id=alpha.id,
                weight=Decimal("0.6000000000"),
                allocated_amount=Decimal("60000.00"),
                shares=Decimal("120.00000000"),
            ),
            alpha,
            it,
        ),
        (
            PortfolioHolding(
                snapshot_id=snapshot_id,
                stock_id=beta.id,
                weight=Decimal("0.4000000000"),
                allocated_amount=Decimal("40000.00"),
                shares=Decimal("80.00000000"),
            ),
            beta,
            energy,
        ),
    )
    explanations = (
        (
            ExplanationItem(
                optimization_run_id=run_id,
                stock_id=alpha.id,
                decision="included",
                primary_reason="high_risk_adjusted_return",
                marginal_return_contribution=Decimal("0.0840000000"),
                marginal_risk_contribution=Decimal("0.1000000000"),
                narrative_text="ALPHA contributes attractive risk-adjusted return.",
            ),
            "ALPHA",
        ),
        (
            ExplanationItem(
                optimization_run_id=run_id,
                stock_id=beta.id,
                decision="included",
                primary_reason="diversification_value",
                marginal_return_contribution=Decimal("0.0560000000"),
                marginal_risk_contribution=Decimal("0.0800000000"),
                narrative_text="BETA improves sector diversification.",
            ),
            "BETA",
        ),
        (
            ExplanationItem(
                optimization_run_id=run_id,
                decision="excluded",
                primary_reason="sector_cap_binding",
                marginal_return_contribution=Decimal(0),
                marginal_risk_contribution=Decimal(0),
                narrative_text="GAMMA was excluded because the IT cap is binding.",
            ),
            "GAMMA",
        ),
    )
    logs = (
        ConstraintLog(
            optimization_run_id=run_id,
            constraint_name="C4 Sector cap: IT",
            is_binding=True,
            slack_value=Decimal(0),
            shadow_price=Decimal("0.0200000000"),
        ),
    )
    return assemble_report_context(
        snapshot,
        portfolio,
        user,
        run,
        holdings,
        explanations,
        logs,
        analytics_bundle,
        generated_at=datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
    )
