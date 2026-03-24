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
        "history_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("hospital_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("room", sa.String(length=128), nullable=False),
        sa.Column("data", sa.String(length=4000), nullable=False),
    )
    op.create_index("ix_history_records_date", "history_records", ["date"], unique=False)
    op.create_index(
        "ix_history_records_patient_id",
        "history_records",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        "ix_history_records_hospital_id",
        "history_records",
        ["hospital_id"],
        unique=False,
    )
    op.create_index("ix_history_records_doctor_id", "history_records", ["doctor_id"], unique=False)
    op.create_index("ix_history_records_room", "history_records", ["room"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_history_records_room", table_name="history_records")
    op.drop_index("ix_history_records_doctor_id", table_name="history_records")
    op.drop_index("ix_history_records_hospital_id", table_name="history_records")
    op.drop_index("ix_history_records_patient_id", table_name="history_records")
    op.drop_index("ix_history_records_date", table_name="history_records")
    op.drop_table("history_records")
