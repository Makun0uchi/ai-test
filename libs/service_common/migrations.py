from pathlib import Path

from alembic import command
from alembic.config import Config


def run_database_migrations(*, alembic_ini_path: Path, database_url: str) -> None:
    config = Config(str(alembic_ini_path))
    config.set_main_option(
        "script_location",
        str((alembic_ini_path.parent / "migrations").resolve()),
    )
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
