from __future__ import annotations

import argparse
from pathlib import Path


def extract_release_notes(changelog_path: Path, version: str) -> str:
    header = f"## [{version}]"
    collecting = False
    collected: list[str] = []

    for line in changelog_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## ["):
            if collecting:
                break
            if line.startswith(header):
                collecting = True
                continue
        if collecting:
            collected.append(line)

    if not collected:
        raise ValueError(f"Could not find changelog section for version {version}")

    return "\n".join(collected).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    notes = extract_release_notes(Path(args.changelog), args.version)
    Path(args.output).write_text(notes, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
