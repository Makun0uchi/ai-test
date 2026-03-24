from importlib import import_module
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_VERSION_TABLE = "alembic_version"
OUTBOX_CORRELATION_COLUMN = "correlation_id"


def run_database_migrations(*, alembic_ini_path: Path, database_url: str) -> None:
    config = Config(str(alembic_ini_path))
    config.set_main_option(
        "script_location",
        str((alembic_ini_path.parent / "migrations").resolve()),
    )
    config.set_main_option("sqlalchemy.url", database_url)
    _bootstrap_legacy_database_if_needed(
        config=config,
        alembic_ini_path=alembic_ini_path,
        database_url=database_url,
    )
    command.upgrade(config, "head")


def _bootstrap_legacy_database_if_needed(
    *,
    config: Config,
    alembic_ini_path: Path,
    database_url: str,
) -> None:
    engine = sa.create_engine(database_url)
    try:
        inspector = sa.inspect(engine)
        existing_tables = set(inspector.get_table_names())
        if ALEMBIC_VERSION_TABLE in existing_tables or not existing_tables:
            return

        revision_to_stamp = _infer_legacy_revision(
            config=config,
            alembic_ini_path=alembic_ini_path,
            inspector=inspector,
            existing_tables=existing_tables,
        )
    finally:
        engine.dispose()

    if revision_to_stamp is not None:
        command.stamp(config, revision_to_stamp)


def _infer_legacy_revision(
    *,
    config: Config,
    alembic_ini_path: Path,
    inspector: sa.Inspector,
    existing_tables: set[str],
) -> str:
    base_tables, outbox_table = _load_service_table_groups(alembic_ini_path)
    ordered_revisions = _get_ordered_revisions(config)
    head_revision = ordered_revisions[-1]

    if not base_tables.issubset(existing_tables):
        raise RuntimeError(
            "Detected a legacy database without alembic_version, but the schema does not "
            "match a known migration state. Existing tables: "
            f"{sorted(existing_tables)}"
        )

    if outbox_table not in existing_tables:
        return ordered_revisions[0]

    outbox_columns = {column["name"] for column in inspector.get_columns(outbox_table)}
    if OUTBOX_CORRELATION_COLUMN not in outbox_columns:
        return ordered_revisions[1]

    return head_revision


def _load_service_table_groups(alembic_ini_path: Path) -> tuple[set[str], str]:
    service_module = import_module(f"services.{alembic_ini_path.parent.name}.app.models")
    metadata = service_module.Base.metadata
    table_names = set(metadata.tables)
    outbox_tables = sorted(name for name in table_names if "outbox" in name)
    if len(outbox_tables) != 1:
        raise RuntimeError(
            "Expected exactly one outbox table for service "
            f"{alembic_ini_path.parent.name}, got {outbox_tables}"
        )

    outbox_table = outbox_tables[0]
    return table_names - {outbox_table}, outbox_table


def _get_ordered_revisions(config: Config) -> list[str]:
    script_directory = ScriptDirectory.from_config(config)
    revisions = list(reversed(list(script_directory.walk_revisions())))
    return [revision.revision for revision in revisions]
