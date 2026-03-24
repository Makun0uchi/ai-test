from pathlib import Path

import pytest
import sqlalchemy as sa
from libs.service_common.migrations import run_database_migrations

ROOT_DIR = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("service_dir", "expected_tables", "outbox_table"),
    [
        (
            "account_service",
            {
                "accounts",
                "roles",
                "account_roles",
                "refresh_tokens",
                "account_outbox",
                "alembic_version",
            },
            "account_outbox",
        ),
        (
            "hospital_service",
            {"hospitals", "hospital_rooms", "hospital_outbox", "alembic_version"},
            "hospital_outbox",
        ),
        (
            "timetable_service",
            {"timetables", "appointments", "timetable_outbox", "alembic_version"},
            "timetable_outbox",
        ),
        (
            "document_service",
            {"history_records", "history_index_outbox", "alembic_version"},
            "history_index_outbox",
        ),
    ],
)
def test_initial_migrations_create_expected_tables(
    tmp_path: Path,
    service_dir: str,
    expected_tables: set[str],
    outbox_table: str,
) -> None:
    database_path = tmp_path / f"{service_dir}.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    alembic_ini_path = ROOT_DIR / "services" / service_dir / "alembic.ini"

    run_database_migrations(alembic_ini_path=alembic_ini_path, database_url=database_url)
    run_database_migrations(alembic_ini_path=alembic_ini_path, database_url=database_url)

    engine = sa.create_engine(database_url)
    try:
        inspector = sa.inspect(engine)
        assert expected_tables.issubset(set(inspector.get_table_names()))
        outbox_columns = {column["name"] for column in inspector.get_columns(outbox_table)}
        assert "correlation_id" in outbox_columns
    finally:
        engine.dispose()
