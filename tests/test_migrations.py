from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from libs.service_common.migrations import run_database_migrations

ROOT_DIR = Path(__file__).resolve().parents[1]
MAX_ALEMBIC_REVISION_ID_LENGTH = 32


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


@pytest.mark.parametrize(
    ("service_dir", "legacy_revision"),
    [
        ("account_service", "0001_initial"),
        ("account_service", "0002_account_outbox"),
        ("hospital_service", "0001_initial"),
        ("hospital_service", "0002_hospital_outbox"),
        ("timetable_service", "0001_initial"),
        ("timetable_service", "0002_timetable_outbox"),
        ("document_service", "0001_initial"),
        ("document_service", "0002_history_index_outbox"),
    ],
)
def test_legacy_schema_without_alembic_version_bootstraps_to_head(
    tmp_path: Path,
    service_dir: str,
    legacy_revision: str,
) -> None:
    database_path = tmp_path / f"{service_dir}_{legacy_revision}.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    alembic_ini_path = ROOT_DIR / "services" / service_dir / "alembic.ini"

    config = _build_alembic_config(alembic_ini_path=alembic_ini_path, database_url=database_url)
    command.upgrade(config, legacy_revision)

    engine = sa.create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(sa.text("DROP TABLE alembic_version"))
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "service_dir",
    [
        "account_service",
        "hospital_service",
        "timetable_service",
        "document_service",
    ],
)
def test_revision_ids_fit_postgresql_alembic_version_limit(service_dir: str) -> None:
    alembic_ini_path = ROOT_DIR / "services" / service_dir / "alembic.ini"
    config = _build_alembic_config(
        alembic_ini_path=alembic_ini_path,
        database_url="sqlite+pysqlite:///:memory:",
    )
    script_directory = ScriptDirectory.from_config(config)

    for revision in script_directory.walk_revisions():
        assert len(revision.revision) <= MAX_ALEMBIC_REVISION_ID_LENGTH


def _build_alembic_config(*, alembic_ini_path: Path, database_url: str) -> Config:
    config = Config(str(alembic_ini_path))
    config.set_main_option(
        "script_location",
        str((alembic_ini_path.parent / "migrations").resolve()),
    )
    config.set_main_option("sqlalchemy.url", database_url)
    return config
