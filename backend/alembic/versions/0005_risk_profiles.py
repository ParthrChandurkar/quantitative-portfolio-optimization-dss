"""Persist personalized questionnaire risk profiles.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_risk_profiles",
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
        sa.Column("questionnaire_answers", postgresql.JSONB(), nullable=False),
        sa.Column("predicted_category", sa.String(32), nullable=False),
        sa.Column("category_confidence", sa.Numeric(20, 10), nullable=False),
        sa.Column("recommended_constraints", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_user_risk_profiles_user_created_at",
        "user_risk_profiles",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_risk_profiles_user_created_at", table_name="user_risk_profiles"
    )
    op.drop_table("user_risk_profiles")
