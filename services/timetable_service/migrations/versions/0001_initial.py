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
        "timetables",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("hospital_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("room", sa.String(length=128), nullable=False),
    )
    op.create_index("ix_timetables_hospital_id", "timetables", ["hospital_id"], unique=False)
    op.create_index("ix_timetables_doctor_id", "timetables", ["doctor_id"], unique=False)
    op.create_index("ix_timetables_starts_at", "timetables", ["starts_at"], unique=False)
    op.create_index("ix_timetables_ends_at", "timetables", ["ends_at"], unique=False)
    op.create_index("ix_timetables_room", "timetables", ["room"], unique=False)

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "timetable_id",
            sa.Integer(),
            sa.ForeignKey("timetables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("timetable_id", "time", name="uq_timetable_appointment_time"),
    )
    op.create_index("ix_appointments_timetable_id", "appointments", ["timetable_id"], unique=False)
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"], unique=False)
    op.create_index("ix_appointments_time", "appointments", ["time"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_appointments_time", table_name="appointments")
    op.drop_index("ix_appointments_patient_id", table_name="appointments")
    op.drop_index("ix_appointments_timetable_id", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index("ix_timetables_room", table_name="timetables")
    op.drop_index("ix_timetables_ends_at", table_name="timetables")
    op.drop_index("ix_timetables_starts_at", table_name="timetables")
    op.drop_index("ix_timetables_doctor_id", table_name="timetables")
    op.drop_index("ix_timetables_hospital_id", table_name="timetables")
    op.drop_table("timetables")
