"""Track return-estimation methods and ML forecast training runs.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "optimization_runs",
        sa.Column(
            "return_estimation_method",
            sa.String(32),
            nullable=True,
            server_default="historical_mean",
        ),
    )
    op.execute(
        "UPDATE optimization_runs SET return_estimation_method = "
        "'historical_mean' WHERE return_estimation_method IS NULL"
    )
    op.create_table(
        "ml_forecast_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("estimation_end_date", sa.Date(), nullable=False),
        sa.Column("model_artifact_path", sa.String(1024), nullable=False),
        sa.Column("feature_importances", postgresql.JSONB(), nullable=False),
        sa.Column("training_row_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("ml_forecast_runs")
    op.drop_column("optimization_runs", "return_estimation_method")
