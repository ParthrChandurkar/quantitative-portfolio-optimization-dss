from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsBundle
from app.db.models import (
    ConstraintLog,
    ExplanationItem,
    OptimizationRun,
    Portfolio,
    PortfolioHolding,
    PortfolioSnapshot,
    Sector,
    Stock,
    StockPrice,
    User,
)
from app.optimization.data import MarketData
from app.reports.context_builder import (
    ReportContext,
    load_report_context,
    model_formulation,
)


def test_context_reuses_numeric_values_exactly(
    report_context: ReportContext,
    analytics_bundle: AnalyticsBundle,
) -> None:
    assert report_context.metrics.expected_return == Decimal("0.1400000000")
    assert report_context.metrics.expected_volatility == Decimal("0.1800000000")
    assert report_context.metrics.sharpe_ratio == Decimal("0.6666666667")
    assert report_context.metrics.diversification_score == Decimal("82.5000000000")
    assert report_context.holdings[0].weight == Decimal("0.6000000000")
    assert report_context.holdings[0].allocated_amount_inr == Decimal("60000.00")
    assert report_context.configured_constraints.target_return == Decimal("0.1400000000")
    assert report_context.constraint_rows[0].shadow_price == Decimal("0.0200000000")
    assert report_context.analytics is analytics_bundle
    assert report_context.analytics.risk_return.expected_return == 0.14
    assert report_context.notable_exclusions[0].symbol == "GAMMA"
    assert report_context.shadow_price_insights[0].shadow_price == 0.02


def test_model_formulation_labels_phase4_solver_families() -> None:
    assert model_formulation("SciPy").startswith("Continuous quadratic")
    assert model_formulation("PuLP").startswith("Mixed-Integer")
    assert model_formulation("OR-Tools").startswith("Hybrid CP-SAT")


async def test_load_context_reads_owned_snapshot_and_delegates_analytics(
    session: AsyncSession,
    monkeypatch,
    analytics_bundle: AnalyticsBundle,
) -> None:
    user_id, portfolio_id, run_id, snapshot_id = (uuid.uuid4() for _ in range(4))
    user = User(
        id=user_id,
        email="context@example.com",
        password_hash="hash",
        full_name="Context Investor",
    )
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=user_id,
        name="Context Portfolio",
        is_active=True,
    )
    run = OptimizationRun(
        id=run_id,
        portfolio_id=portfolio_id,
        solver_used="SciPy",
        budget=Decimal(100000),
        target_return=Decimal("0.12"),
        risk_tolerance=None,
        max_single_weight=Decimal("0.60"),
        min_holdings=2,
        sector_constraints={"IT": 0.60, "Energy": 0.60},
        status="OPTIMAL",
        solve_time_ms=25,
    )
    snapshot = PortfolioSnapshot(
        id=snapshot_id,
        portfolio_id=portfolio_id,
        optimization_run_id=run_id,
        label="Owned snapshot",
        expected_return=Decimal("0.12"),
        expected_volatility=Decimal("0.16"),
        sharpe_ratio=Decimal("0.75"),
        diversification_score=Decimal(80),
        is_baseline=True,
    )
    it = Sector(name="IT")
    energy = Sector(name="Energy")
    alpha = Stock(symbol="ALPHA", company_name="Alpha Ltd", sector=it)
    beta = Stock(symbol="BETA", company_name="Beta Ltd", sector=energy)
    session.add_all([user, portfolio, run, snapshot, alpha, beta])
    await session.flush()
    for stock, weight in ((alpha, Decimal("0.60")), (beta, Decimal("0.40"))):
        session.add(
            PortfolioHolding(
                snapshot_id=snapshot_id,
                stock_id=stock.id,
                weight=weight,
                allocated_amount=Decimal(100000) * weight,
                shares=Decimal(100),
            )
        )
        session.add(
            StockPrice(
                stock_id=stock.id,
                trade_date=date(2025, 12, 31),
                open=Decimal(100),
                high=Decimal(101),
                low=Decimal(99),
                close=Decimal(100),
                adj_close=Decimal(100),
                volume=1_000,
                daily_return=Decimal("0.01"),
            )
        )
        session.add(
            ExplanationItem(
                optimization_run_id=run_id,
                stock_id=stock.id,
                decision="included",
                primary_reason="diversification_value",
                narrative_text=f"{stock.symbol} contributes to the portfolio.",
            )
        )
    session.add(
        ConstraintLog(
            optimization_run_id=run_id,
            constraint_name="C4 Sector cap: IT",
            is_binding=True,
            slack_value=Decimal(0),
            shadow_price=Decimal("0.01"),
        )
    )
    await session.commit()

    async def fake_market_data(*_args, **_kwargs) -> MarketData:
        history = np.asarray([[0.01, 0.00], [0.00, 0.01], [0.02, -0.01]])
        return MarketData(
            ("ALPHA", "BETA"),
            np.asarray([0.12, 0.10]),
            np.asarray([[0.02, 0.001], [0.001, 0.03]]),
            history,
            3,
            False,
        )

    captured = {}

    async def fake_analytics(snapshot_input, universe, selected_range, *, session):
        captured["weights"] = snapshot_input.weights
        captured["symbols"] = universe.symbols
        captured["range"] = selected_range
        return analytics_bundle

    monkeypatch.setattr(
        "app.reports.context_builder.build_market_data", fake_market_data
    )
    monkeypatch.setattr("app.reports.context_builder.get_analytics", fake_analytics)
    context = await load_report_context(session, snapshot_id, user_id)

    assert context.portfolio_name == "Context Portfolio"
    assert tuple(holding.symbol for holding in context.holdings) == ("ALPHA", "BETA")
    assert context.analytics is analytics_bundle
    assert captured["weights"] == {"ALPHA": 0.6, "BETA": 0.4}
    assert captured["symbols"] == ("ALPHA", "BETA")
    assert captured["range"].end_date == date(2025, 12, 31)
