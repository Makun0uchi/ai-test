"""add history outbox correlation id

Revision ID: 0003_history_outbox_correlation
Revises: 0002_history_index_outbox
Create Date: 2026-03-24 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_history_outbox_correlation"
down_revision: str | None = "0002_history_index_outbox"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "history_index_outbox",
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_history_index_outbox_correlation_id",
        "history_index_outbox",
        ["correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_history_index_outbox_correlation_id",
        table_name="history_index_outbox",
    )
    op.drop_column("history_index_outbox", "correlation_id")
