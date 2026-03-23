from pathlib import Path


def read_version() -> str:
    version_file = Path(__file__).resolve().parents[2] / "VERSION"
    return version_file.read_text(encoding="utf-8").strip()
