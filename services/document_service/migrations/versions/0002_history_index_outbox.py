"""add history index outbox

Revision ID: 0002_history_index_outbox
Revises: 0001_initial
Create Date: 2026-03-24 00:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_history_index_outbox"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "history_index_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("history_id", sa.Integer(), nullable=False),
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
    )
    op.create_index(
        "ix_history_index_outbox_history_id",
        "history_index_outbox",
        ["history_id"],
        unique=False,
    )
    op.create_index(
        "ix_history_index_outbox_event_type",
        "history_index_outbox",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_history_index_outbox_routing_key",
        "history_index_outbox",
        ["routing_key"],
        unique=False,
    )
    op.create_index(
        "ix_history_index_outbox_published_at",
        "history_index_outbox",
        ["published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_history_index_outbox_published_at", table_name="history_index_outbox")
    op.drop_index("ix_history_index_outbox_routing_key", table_name="history_index_outbox")
    op.drop_index("ix_history_index_outbox_event_type", table_name="history_index_outbox")
    op.drop_index("ix_history_index_outbox_history_id", table_name="history_index_outbox")
    op.drop_table("history_index_outbox")
