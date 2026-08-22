"""SQLAlchemy 2.0 ORM model definitions for the OptiVest data store."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

UUID = Uuid(as_uuid=True)
JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")
MONEY = Numeric(20, 2)  # All monetary values are Indian rupees (INR).
WEIGHT = Numeric(12, 10)
METRIC = Numeric(20, 10)

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(DeclarativeBase):
    """Base class shared by all ORM models."""

    metadata = metadata


class UUIDPrimaryKeyMixin:
    """Portable UUID generation plus PostgreSQL-side pgcrypto default."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class User(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    risk_profile_default: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolios: Mapped[list[Portfolio]] = relationship(back_populates="user")
    reports: Mapped[list[Report]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user")
    risk_profiles: Mapped[list[UserRiskProfile]] = relationship(back_populates="user")
    assistant_query_logs: Mapped[list[AssistantQueryLog]] = relationship(back_populates="user")


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    """Hashed, rotatable JWT refresh-token state for Phase 9 authentication."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("refresh_tokens.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class Sector(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sectors"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    stocks: Mapped[list[Stock]] = relationship(back_populates="sector")


class Stock(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False
    )
    industry: Mapped[str | None] = mapped_column(String(160))
    listed_since: Mapped[date | None] = mapped_column(Date)

    sector: Mapped[Sector] = relationship(back_populates="stocks")
    prices: Mapped[list[StockPrice]] = relationship(back_populates="stock")
    fundamentals: Mapped[list[StockFundamental]] = relationship(back_populates="stock")
    technical_indicators: Mapped[list[StockTechnicalIndicator]] = relationship(
        back_populates="stock"
    )


class StockPrice(UUIDPrimaryKeyMixin, Base):
    """Indexed daily prices supporting the NFR-2 market-data capacity target."""

    __tablename__ = "stock_prices"
    __table_args__ = (
        UniqueConstraint("stock_id", "trade_date", name="uq_stock_prices_stock_date"),
        Index("ix_stock_prices_stock_trade_date_desc", "stock_id", text("trade_date DESC")),
    )

    stock_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    high: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    low: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    close: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    adj_close: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    daily_return: Mapped[Decimal | None] = mapped_column(METRIC)

    stock: Mapped[Stock] = relationship(back_populates="prices")


class StockFundamental(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stock_fundamentals"
    __table_args__ = (
        UniqueConstraint(
            "stock_id", "as_of_date", name="uq_stock_fundamentals_stock_date"
        ),
        Index(
            "ix_stock_fundamentals_stock_as_of_date_desc",
            "stock_id",
            text("as_of_date DESC"),
        ),
    )

    stock_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    pe_ratio: Mapped[Decimal | None] = mapped_column(METRIC)
    pb_ratio: Mapped[Decimal | None] = mapped_column(METRIC)
    market_cap: Mapped[Decimal | None] = mapped_column(MONEY)
    dividend_yield: Mapped[Decimal | None] = mapped_column(METRIC)
    eps: Mapped[Decimal | None] = mapped_column(MONEY)
    beta: Mapped[Decimal | None] = mapped_column(METRIC)

    stock: Mapped[Stock] = relationship(back_populates="fundamentals")


class StockTechnicalIndicator(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stock_technical_indicators"
    __table_args__ = (
        UniqueConstraint(
            "stock_id", "trade_date", name="uq_stock_technical_stock_date"
        ),
        Index(
            "ix_stock_technical_stock_trade_date_desc",
            "stock_id",
            text("trade_date DESC"),
        ),
    )

    stock_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    sma_50: Mapped[Decimal | None] = mapped_column(MONEY)
    sma_200: Mapped[Decimal | None] = mapped_column(MONEY)
    rsi_14: Mapped[Decimal | None] = mapped_column(METRIC)
    macd: Mapped[Decimal | None] = mapped_column(METRIC)
    volatility_annualized: Mapped[Decimal | None] = mapped_column(METRIC)

    stock: Mapped[Stock] = relationship(back_populates="technical_indicators")


class Portfolio(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "portfolios"
    __table_args__ = (Index("ix_portfolios_user_id", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    user: Mapped[User] = relationship(back_populates="portfolios")
    optimization_runs: Mapped[list[OptimizationRun]] = relationship(back_populates="portfolio")
    snapshots: Mapped[list[PortfolioSnapshot]] = relationship(back_populates="portfolio")
    walk_forward_runs: Mapped[list[WalkForwardRun]] = relationship(
        back_populates="portfolio"
    )
    assistant_query_logs: Mapped[list[AssistantQueryLog]] = relationship(
        back_populates="portfolio"
    )


class OptimizationRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "optimization_runs"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    solver_used: Mapped[str] = mapped_column(String(80), nullable=False)
    budget: Mapped[Decimal] = mapped_column(MONEY, nullable=False)  # INR
    target_return: Mapped[Decimal | None] = mapped_column(METRIC)
    risk_tolerance: Mapped[Decimal | None] = mapped_column(METRIC)
    max_single_weight: Mapped[Decimal] = mapped_column(WEIGHT, nullable=False)
    min_holdings: Mapped[int] = mapped_column(Integer, nullable=False)
    sector_constraints: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, default=dict, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    return_estimation_method: Mapped[str | None] = mapped_column(
        String(32), default="historical_mean", server_default="historical_mean"
    )
    solve_time_ms: Mapped[int | None] = mapped_column(Integer)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="optimization_runs")
    snapshots: Mapped[list[PortfolioSnapshot]] = relationship(back_populates="optimization_run")
    explanation_items: Mapped[list[ExplanationItem]] = relationship(
        back_populates="optimization_run"
    )
    constraint_logs: Mapped[list[ConstraintLog]] = relationship(
        back_populates="optimization_run"
    )


class PortfolioSnapshot(UUIDPrimaryKeyMixin, Base):
    """Immutable decision snapshot persisted atomically under FR-8 and NFR-4."""

    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        Index(
            "ix_portfolio_snapshots_portfolio_created_at_desc",
            "portfolio_id",
            text("created_at DESC"),
        ),
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    expected_return: Mapped[Decimal | None] = mapped_column(METRIC)
    expected_volatility: Mapped[Decimal | None] = mapped_column(METRIC)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(METRIC)
    diversification_score: Mapped[Decimal | None] = mapped_column(METRIC)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="snapshots")
    optimization_run: Mapped[OptimizationRun] = relationship(back_populates="snapshots")
    holdings: Mapped[list[PortfolioHolding]] = relationship(back_populates="snapshot")
    reports: Mapped[list[Report]] = relationship(back_populates="snapshot")
    scenarios_as_base: Mapped[list[ScenarioRun]] = relationship(
        back_populates="base_snapshot", foreign_keys="ScenarioRun.base_snapshot_id"
    )
    scenarios_as_result: Mapped[list[ScenarioRun]] = relationship(
        back_populates="resulting_snapshot", foreign_keys="ScenarioRun.resulting_snapshot_id"
    )


class PortfolioHolding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "portfolio_holdings"
    __table_args__ = (Index("ix_portfolio_holdings_snapshot_id", "snapshot_id"),)

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("portfolio_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=False
    )
    weight: Mapped[Decimal] = mapped_column(WEIGHT, nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)  # INR
    shares: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    snapshot: Mapped[PortfolioSnapshot] = relationship(back_populates="holdings")
    stock: Mapped[Stock] = relationship()


class ExplanationItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "explanation_items"
    __table_args__ = (Index("ix_explanation_items_optimization_run_id", "optimization_run_id"),)

    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("stocks.id", ondelete="RESTRICT")
    )
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    primary_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    marginal_return_contribution: Mapped[Decimal | None] = mapped_column(METRIC)
    marginal_risk_contribution: Mapped[Decimal | None] = mapped_column(METRIC)
    binding_constraint: Mapped[str | None] = mapped_column(String(255))
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)

    optimization_run: Mapped[OptimizationRun] = relationship(
        back_populates="explanation_items"
    )
    stock: Mapped[Stock | None] = relationship()


class ConstraintLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "constraint_log"
    __table_args__ = (Index("ix_constraint_log_optimization_run_id", "optimization_run_id"),)

    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False
    )
    constraint_name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_binding: Mapped[bool] = mapped_column(Boolean, nullable=False)
    slack_value: Mapped[Decimal | None] = mapped_column(METRIC)
    shadow_price: Mapped[Decimal | None] = mapped_column(METRIC)

    optimization_run: Mapped[OptimizationRun] = relationship(
        back_populates="constraint_logs"
    )


class ScenarioRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "scenario_runs"

    base_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("portfolio_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    resulting_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("portfolio_snapshots.id", ondelete="SET NULL")
    )
    scenario_type: Mapped[str] = mapped_column(String(80), nullable=False)
    shock_parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, default=dict, nullable=False
    )
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    base_snapshot: Mapped[PortfolioSnapshot] = relationship(
        back_populates="scenarios_as_base", foreign_keys=[base_snapshot_id]
    )
    resulting_snapshot: Mapped[PortfolioSnapshot | None] = relationship(
        back_populates="scenarios_as_result", foreign_keys=[resulting_snapshot_id]
    )


class Report(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("portfolio_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="reports")
    snapshot: Mapped[PortfolioSnapshot] = relationship(back_populates="reports")


class CovarianceCache(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "covariance_cache"
    __table_args__ = (
        UniqueConstraint(
            "universe_hash",
            "lookback_days",
            "as_of_date",
            name="uq_covariance_cache_universe_lookback_date",
        ),
    )

    universe_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    matrix: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MlForecastRun(UUIDPrimaryKeyMixin, Base):
    """Training provenance for one leakage-safe ML return forecast artifact."""

    __tablename__ = "ml_forecast_runs"

    estimation_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    model_artifact_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    feature_importances: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    training_row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserRiskProfile(UUIDPrimaryKeyMixin, Base):
    """Auditable questionnaire response, classifier output, and editable defaults."""

    __tablename__ = "user_risk_profiles"
    __table_args__ = (Index("ix_user_risk_profiles_user_created_at", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    questionnaire_answers: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    predicted_category: Mapped[str] = mapped_column(String(32), nullable=False)
    category_confidence: Mapped[Decimal] = mapped_column(METRIC, nullable=False)
    recommended_constraints: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="risk_profiles")


class AssistantQueryLog(UUIDPrimaryKeyMixin, Base):
    """Audit log for every answered or safely-fallback portfolio question."""

    __tablename__ = "assistant_query_logs"
    __table_args__ = (
        Index("ix_assistant_query_logs_user_created_at", "user_id", "created_at"),
        Index("ix_assistant_query_logs_portfolio_created_at", "portfolio_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    classified_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(METRIC, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="assistant_query_logs")
    portfolio: Mapped[Portfolio] = relationship(back_populates="assistant_query_logs")


class WalkForwardRun(UUIDPrimaryKeyMixin, Base):
    """Persisted, reproducible walk-forward validation result."""

    __tablename__ = "walk_forward_runs"
    __table_args__ = (
        Index("ix_walk_forward_runs_portfolio_created_at", "portfolio_id", "created_at"),
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    rebalance_frequency: Mapped[str] = mapped_column(String(24), nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    constraints_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT, nullable=False
    )
    result: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="walk_forward_runs")
