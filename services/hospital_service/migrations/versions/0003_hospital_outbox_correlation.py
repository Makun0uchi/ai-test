"""add hospital outbox correlation id

Revision ID: 0003_hospital_outbox_correlation
Revises: 0002_hospital_outbox
Create Date: 2026-03-24 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_hospital_outbox_correlation"
down_revision: str | None = "0002_hospital_outbox"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "hospital_outbox",
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_hospital_outbox_correlation_id",
        "hospital_outbox",
        ["correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hospital_outbox_correlation_id", table_name="hospital_outbox")
    op.drop_column("hospital_outbox", "correlation_id")
