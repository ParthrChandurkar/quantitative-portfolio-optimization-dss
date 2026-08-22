"""Persist personalized risk and anomaly alerts.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolio_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "stock_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stocks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("grounding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "acknowledged",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_alerts_user_acknowledged_created_at",
        "alerts",
        ["user_id", "acknowledged", "created_at"],
    )
    op.create_index(
        "ix_alerts_portfolio_created_at", "alerts", ["portfolio_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_portfolio_created_at", table_name="alerts")
    op.drop_index("ix_alerts_user_acknowledged_created_at", table_name="alerts")
    op.drop_table("alerts")
