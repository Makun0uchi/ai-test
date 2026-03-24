"""add timetable outbox correlation id

Revision ID: 0003_timetable_outbox_corr
Revises: 0002_timetable_outbox
Create Date: 2026-03-24 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_timetable_outbox_corr"
down_revision: str | None = "0002_timetable_outbox"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "timetable_outbox",
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_timetable_outbox_correlation_id",
        "timetable_outbox",
        ["correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_timetable_outbox_correlation_id", table_name="timetable_outbox")
    op.drop_column("timetable_outbox", "correlation_id")
