"""Schema integrity tests for Phase 2 ORM models."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Base,
    ConstraintLog,
    CovarianceCache,
    ExplanationItem,
    OptimizationRun,
    Portfolio,
    PortfolioHolding,
    PortfolioSnapshot,
    Report,
    ScenarioRun,
    Sector,
    Stock,
    StockFundamental,
    StockPrice,
    StockTechnicalIndicator,
    User,
)

EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "sectors",
    "stocks",
    "stock_prices",
    "stock_fundamentals",
    "stock_technical_indicators",
    "portfolios",
    "optimization_runs",
    "portfolio_snapshots",
    "portfolio_holdings",
    "explanation_items",
    "constraint_log",
    "scenario_runs",
    "reports",
    "covariance_cache",
    "walk_forward_runs",
    "ml_forecast_runs",
}


def make_price(stock_id: uuid.UUID, trade_date: date) -> StockPrice:
    return StockPrice(
        stock_id=stock_id,
        trade_date=trade_date,
        open=Decimal(100),
        high=Decimal(110),
        low=Decimal(95),
        close=Decimal(105),
        adj_close=Decimal(105),
        volume=1000,
    )


async def seed_stock(session: AsyncSession) -> Stock:
    sector = Sector(name="Financial Services")
    stock = Stock(
        symbol="HDFCBANK",
        company_name="HDFC Bank Limited",
        sector=sector,
        industry="Private Banks",
    )
    session.add(stock)
    await session.commit()
    return stock


async def seed_decision_graph(session: AsyncSession) -> tuple[User, Stock, PortfolioSnapshot]:
    stock = await seed_stock(session)
    user = User(email="parth@example.com", password_hash="hash", full_name="Parth")
    portfolio = Portfolio(user=user, name="Balanced INR Portfolio")
    run = OptimizationRun(
        portfolio=portfolio,
        solver_used="PuLP/CBC",
        budget=Decimal("2500000.00"),
        max_single_weight=Decimal("0.20"),
        min_holdings=5,
        sector_constraints={"Financial Services": "0.30"},
        status="OPTIMAL",
    )
    snapshot = PortfolioSnapshot(
        portfolio=portfolio,
        optimization_run=run,
        label="Baseline",
        is_baseline=True,
    )
    session.add_all([user, portfolio, run, snapshot])
    await session.commit()
    return user, stock, snapshot


async def test_all_expected_tables_and_foreign_keys_exist(engine) -> None:
    """Verifies FR-2, FR-8, NFR-2, and the complete relationship graph."""

    def inspect_schema(connection) -> tuple[set[str], dict[str, set[str]]]:
        schema = inspect(connection)
        tables = set(schema.get_table_names())
        foreign_keys = {
            table: {
                fk["referred_table"]
                for fk in schema.get_foreign_keys(table)
                if fk["referred_table"] is not None
            }
            for table in tables
        }
        return tables, foreign_keys

    async with engine.connect() as connection:
        tables, foreign_keys = await connection.run_sync(inspect_schema)

    assert tables == EXPECTED_TABLES
    assert foreign_keys["stocks"] == {"sectors"}
    assert foreign_keys["refresh_tokens"] == {"users", "refresh_tokens"}
    assert foreign_keys["stock_prices"] == {"stocks"}
    assert foreign_keys["portfolio_snapshots"] == {"portfolios", "optimization_runs"}
    assert foreign_keys["scenario_runs"] == {"portfolio_snapshots"}
    assert foreign_keys["reports"] == {"users", "portfolio_snapshots"}
    assert foreign_keys["walk_forward_runs"] == {"portfolios"}


@pytest.mark.parametrize(
    ("factory", "unique_description"),
    [
        (lambda stock: make_price(stock.id, date(2026, 1, 2)), "stock price date"),
        (
            lambda stock: StockFundamental(stock_id=stock.id, as_of_date=date(2026, 1, 2)),
            "fundamental date",
        ),
        (
            lambda stock: StockTechnicalIndicator(
                stock_id=stock.id, trade_date=date(2026, 1, 2)
            ),
            "indicator date",
        ),
    ],
)
async def test_dated_stock_natural_keys_are_unique(
    session: AsyncSession, factory, unique_description: str
) -> None:
    """NFR-7: duplicate symbol-date observations must be rejected."""

    stock = await seed_stock(session)
    session.add(factory(stock))
    await session.commit()
    session.add(factory(stock))
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        await session.commit()
    await session.rollback()
    assert unique_description


async def test_user_email_stock_symbol_and_covariance_key_are_unique(
    session: AsyncSession,
) -> None:
    user = User(email="unique@example.com", password_hash="hash", full_name="One")
    session.add(user)
    await session.commit()
    session.add(User(email=user.email, password_hash="hash2", full_name="Two"))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    stock = await seed_stock(session)
    duplicate_sector = await session.scalar(select(Sector).where(Sector.name == stock.sector.name))
    session.add(
        Stock(
            symbol=stock.symbol,
            company_name="Duplicate",
            sector_id=duplicate_sector.id,
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    cache_values = {
        "universe_hash": "sha256:abc",
        "lookback_days": 252,
        "as_of_date": date(2026, 1, 2),
        "matrix": {"HDFCBANK": {"HDFCBANK": 0.04}},
    }
    session.add(CovarianceCache(**cache_values))
    await session.commit()
    session.add(CovarianceCache(**cache_values))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_every_foreign_key_is_enforced(session: AsyncSession) -> None:
    """NFR-4: failed relationship writes roll back without retained invalid rows."""

    missing = uuid.uuid4()
    factories = [
        lambda: Stock(symbol="NOFK", company_name="Invalid", sector_id=missing),
        lambda: make_price(missing, date(2026, 1, 1)),
        lambda: StockFundamental(stock_id=missing, as_of_date=date(2026, 1, 1)),
        lambda: StockTechnicalIndicator(stock_id=missing, trade_date=date(2026, 1, 1)),
        lambda: Portfolio(user_id=missing, name="Invalid"),
        lambda: OptimizationRun(
            portfolio_id=missing,
            solver_used="SciPy",
            budget=Decimal(1),
            max_single_weight=Decimal(1),
            min_holdings=1,
            sector_constraints={},
            status="OPTIMAL",
        ),
        lambda: PortfolioSnapshot(
            portfolio_id=missing, optimization_run_id=missing, label="Invalid"
        ),
        lambda: PortfolioHolding(
            snapshot_id=missing,
            stock_id=missing,
            weight=Decimal(1),
            allocated_amount=Decimal(1),
            shares=Decimal(1),
        ),
        lambda: ExplanationItem(
            optimization_run_id=missing,
            stock_id=missing,
            decision="SELECTED",
            primary_reason="Invalid",
            narrative_text="Invalid",
        ),
        lambda: ConstraintLog(
            optimization_run_id=missing, constraint_name="budget", is_binding=True
        ),
        lambda: ScenarioRun(
            base_snapshot_id=missing,
            resulting_snapshot_id=missing,
            scenario_type="MARKET_CRASH",
            shock_parameters={},
        ),
        lambda: Report(
            user_id=missing,
            snapshot_id=missing,
            report_type="SUMMARY",
            file_path="report.pdf",
        ),
    ]
    for factory in factories:
        session.add(factory())
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


async def test_complete_decision_relationships_and_inr_precision(
    session: AsyncSession,
) -> None:
    """FR-8: persist the decision graph with rupee amounts and fixed precision."""

    user, stock, snapshot = await seed_decision_graph(session)
    holding = PortfolioHolding(
        snapshot_id=snapshot.id,
        stock_id=stock.id,
        weight=Decimal("0.1840000000"),
        allocated_amount=Decimal("460000.55"),
        shares=Decimal("281.25000000"),
    )
    report = Report(
        user_id=user.id,
        snapshot_id=snapshot.id,
        report_type="OPTIMIZATION",
        file_path="reports/optimization.pdf",
    )
    session.add_all([holding, report])
    await session.commit()
    stored = await session.get(PortfolioHolding, holding.id)
    assert stored is not None
    assert stored.allocated_amount == Decimal("460000.55")
    assert stored.weight == Decimal("0.1840000000")


def test_all_tables_have_uuid_primary_keys() -> None:
    for table in Base.metadata.sorted_tables:
        primary_keys = list(table.primary_key.columns)
        assert [column.name for column in primary_keys] == ["id"]
        assert primary_keys[0].type.python_type is uuid.UUID
