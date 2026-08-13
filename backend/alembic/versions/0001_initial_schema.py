"""Create the initial OptiVest PostgreSQL schema.

Revision ID: 0001
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
MONEY = sa.Numeric(20, 2)
WEIGHT = sa.Numeric(12, 10)
METRIC = sa.Numeric(20, 10)


def uuid_pk() -> sa.Column[object]:
    return sa.Column(
        "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def upgrade() -> None:
    """Create the schema and all required indexes."""

    # NFR-3: pgcrypto provides database-side UUID generation without sequential IDs.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        uuid_pk(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("risk_profile_default", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "sectors",
        uuid_pk(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.UniqueConstraint("name", name="uq_sectors_name"),
    )
    op.create_table(
        "stocks",
        uuid_pk(),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("sector_id", UUID, nullable=False),
        sa.Column("industry", sa.String(160)),
        sa.Column("listed_since", sa.Date()),
        sa.ForeignKeyConstraint(["sector_id"], ["sectors.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("symbol", name="uq_stocks_symbol"),
    )
    op.create_table(
        "stock_prices",
        uuid_pk(),
        sa.Column("stock_id", UUID, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", MONEY, nullable=False),
        sa.Column("high", MONEY, nullable=False),
        sa.Column("low", MONEY, nullable=False),
        sa.Column("close", MONEY, nullable=False),
        sa.Column("adj_close", MONEY, nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("daily_return", METRIC),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("stock_id", "trade_date", name="uq_stock_prices_stock_date"),
    )
    op.create_index(
        "ix_stock_prices_stock_trade_date_desc",
        "stock_prices",
        ["stock_id", sa.text("trade_date DESC")],
    )
    op.create_table(
        "stock_fundamentals",
        uuid_pk(),
        sa.Column("stock_id", UUID, nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("pe_ratio", METRIC),
        sa.Column("pb_ratio", METRIC),
        sa.Column("market_cap", MONEY),
        sa.Column("dividend_yield", METRIC),
        sa.Column("eps", MONEY),
        sa.Column("beta", METRIC),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "stock_id", "as_of_date", name="uq_stock_fundamentals_stock_date"
        ),
    )
    op.create_index(
        "ix_stock_fundamentals_stock_as_of_date_desc",
        "stock_fundamentals",
        ["stock_id", sa.text("as_of_date DESC")],
    )
    op.create_table(
        "stock_technical_indicators",
        uuid_pk(),
        sa.Column("stock_id", UUID, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("sma_50", MONEY),
        sa.Column("sma_200", MONEY),
        sa.Column("rsi_14", METRIC),
        sa.Column("macd", METRIC),
        sa.Column("volatility_annualized", METRIC),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("stock_id", "trade_date", name="uq_stock_technical_stock_date"),
    )
    op.create_index(
        "ix_stock_technical_stock_trade_date_desc",
        "stock_technical_indicators",
        ["stock_id", sa.text("trade_date DESC")],
    )
    op.create_table(
        "portfolios",
        uuid_pk(),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])
    op.create_table(
        "optimization_runs",
        uuid_pk(),
        sa.Column("portfolio_id", UUID, nullable=False),
        sa.Column("solver_used", sa.String(80), nullable=False),
        sa.Column("budget", MONEY, nullable=False, comment="Indian rupees (INR)"),
        sa.Column("target_return", METRIC),
        sa.Column("risk_tolerance", METRIC),
        sa.Column("max_single_weight", WEIGHT, nullable=False),
        sa.Column("min_holdings", sa.Integer(), nullable=False),
        sa.Column("sector_constraints", JSONB, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("solve_time_ms", sa.Integer()),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "portfolio_snapshots",
        uuid_pk(),
        sa.Column("portfolio_id", UUID, nullable=False),
        sa.Column("optimization_run_id", UUID, nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("expected_return", METRIC),
        sa.Column("expected_volatility", METRIC),
        sa.Column("sharpe_ratio", METRIC),
        sa.Column("diversification_score", METRIC),
        sa.Column("is_baseline", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["optimization_run_id"], ["optimization_runs.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_portfolio_snapshots_portfolio_created_at_desc",
        "portfolio_snapshots",
        ["portfolio_id", sa.text("created_at DESC")],
    )
    op.create_table(
        "portfolio_holdings",
        uuid_pk(),
        sa.Column("snapshot_id", UUID, nullable=False),
        sa.Column("stock_id", UUID, nullable=False),
        sa.Column("weight", WEIGHT, nullable=False),
        sa.Column("allocated_amount", MONEY, nullable=False, comment="Indian rupees (INR)"),
        sa.Column("shares", sa.Numeric(20, 8), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["portfolio_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_portfolio_holdings_snapshot_id", "portfolio_holdings", ["snapshot_id"])
    op.create_table(
        "explanation_items",
        uuid_pk(),
        sa.Column("optimization_run_id", UUID, nullable=False),
        sa.Column("stock_id", UUID),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("primary_reason", sa.String(255), nullable=False),
        sa.Column("marginal_return_contribution", METRIC),
        sa.Column("marginal_risk_contribution", METRIC),
        sa.Column("binding_constraint", sa.String(255)),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["optimization_run_id"], ["optimization_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_explanation_items_optimization_run_id", "explanation_items", ["optimization_run_id"]
    )
    op.create_table(
        "constraint_log",
        uuid_pk(),
        sa.Column("optimization_run_id", UUID, nullable=False),
        sa.Column("constraint_name", sa.String(160), nullable=False),
        sa.Column("is_binding", sa.Boolean(), nullable=False),
        sa.Column("slack_value", METRIC),
        sa.Column("shadow_price", METRIC),
        sa.ForeignKeyConstraint(
            ["optimization_run_id"], ["optimization_runs.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_constraint_log_optimization_run_id", "constraint_log", ["optimization_run_id"]
    )
    op.create_table(
        "scenario_runs",
        uuid_pk(),
        sa.Column("base_snapshot_id", UUID, nullable=False),
        sa.Column("resulting_snapshot_id", UUID),
        sa.Column("scenario_type", sa.String(80), nullable=False),
        sa.Column("shock_parameters", JSONB, nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["base_snapshot_id"], ["portfolio_snapshots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["resulting_snapshot_id"], ["portfolio_snapshots.id"], ondelete="SET NULL"
        ),
    )
    op.create_table(
        "reports",
        uuid_pk(),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("snapshot_id", UUID, nullable=False),
        sa.Column("report_type", sa.String(80), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["portfolio_snapshots.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "covariance_cache",
        uuid_pk(),
        sa.Column("universe_hash", sa.String(128), nullable=False),
        sa.Column("lookback_days", sa.Integer(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("matrix", JSONB, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "universe_hash",
            "lookback_days",
            "as_of_date",
            name="uq_covariance_cache_universe_lookback_date",
        ),
    )


def downgrade() -> None:
    """Drop the schema in reverse dependency order."""

    op.drop_table("covariance_cache")
    op.drop_table("reports")
    op.drop_table("scenario_runs")
    op.drop_index("ix_constraint_log_optimization_run_id", table_name="constraint_log")
    op.drop_table("constraint_log")
    op.drop_index("ix_explanation_items_optimization_run_id", table_name="explanation_items")
    op.drop_table("explanation_items")
    op.drop_index("ix_portfolio_holdings_snapshot_id", table_name="portfolio_holdings")
    op.drop_table("portfolio_holdings")
    op.drop_index(
        "ix_portfolio_snapshots_portfolio_created_at_desc", table_name="portfolio_snapshots"
    )
    op.drop_table("portfolio_snapshots")
    op.drop_table("optimization_runs")
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_index(
        "ix_stock_technical_stock_trade_date_desc", table_name="stock_technical_indicators"
    )
    op.drop_table("stock_technical_indicators")
    op.drop_index(
        "ix_stock_fundamentals_stock_as_of_date_desc", table_name="stock_fundamentals"
    )
    op.drop_table("stock_fundamentals")
    op.drop_index("ix_stock_prices_stock_trade_date_desc", table_name="stock_prices")
    op.drop_table("stock_prices")
    op.drop_table("stocks")
    op.drop_table("sectors")
    op.drop_table("users")
