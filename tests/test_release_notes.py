from pathlib import Path

import pytest
from scripts.extract_release_notes import extract_release_notes


def test_extract_release_notes_returns_requested_section(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "## [Unreleased]",
                "",
                "## [1.2.0] - 2026-03-24",
                "",
                "### Added",
                "- Added release automation.",
                "",
                "## [1.1.0] - 2026-03-23",
                "",
                "### Added",
                "- Previous release.",
            ]
        ),
        encoding="utf-8",
    )

    notes = extract_release_notes(changelog, "1.2.0")

    assert notes == "### Added\n- Added release automation.\n"


def test_extract_release_notes_raises_for_missing_version(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Could not find changelog section"):
        extract_release_notes(changelog, "9.9.9")
