"""Persist grounded assistant query audit logs.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_query_logs",
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
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("classified_intent", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Numeric(20, 10), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_assistant_query_logs_user_created_at",
        "assistant_query_logs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_assistant_query_logs_portfolio_created_at",
        "assistant_query_logs",
        ["portfolio_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_query_logs_portfolio_created_at",
        table_name="assistant_query_logs",
    )
    op.drop_index(
        "ix_assistant_query_logs_user_created_at", table_name="assistant_query_logs"
    )
    op.drop_table("assistant_query_logs")
