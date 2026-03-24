"""add hospital outbox

Revision ID: 0002_hospital_outbox
Revises: 0001_initial
Create Date: 2026-03-24 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_hospital_outbox"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hospital_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hospital_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("routing_key", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hospital_outbox_hospital_id",
        "hospital_outbox",
        ["hospital_id"],
        unique=False,
    )
    op.create_index(
        "ix_hospital_outbox_event_type",
        "hospital_outbox",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_hospital_outbox_routing_key",
        "hospital_outbox",
        ["routing_key"],
        unique=False,
    )
    op.create_index(
        "ix_hospital_outbox_published_at",
        "hospital_outbox",
        ["published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hospital_outbox_published_at", table_name="hospital_outbox")
    op.drop_index("ix_hospital_outbox_routing_key", table_name="hospital_outbox")
    op.drop_index("ix_hospital_outbox_event_type", table_name="hospital_outbox")
    op.drop_index("ix_hospital_outbox_hospital_id", table_name="hospital_outbox")
    op.drop_table("hospital_outbox")
