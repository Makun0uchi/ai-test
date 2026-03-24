"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-24 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hospitals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.Column("contact_phone", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_hospitals_name", "hospitals", ["name"], unique=False)

    op.create_table(
        "hospital_rooms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "hospital_id",
            sa.Integer(),
            sa.ForeignKey("hospitals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("hospital_id", "name", name="uq_hospital_room_name"),
    )


def downgrade() -> None:
    op.drop_table("hospital_rooms")
    op.drop_index("ix_hospitals_name", table_name="hospitals")
    op.drop_table("hospitals")
