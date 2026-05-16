from __future__ import annotations

from pathlib import Path

from collections.abc import Iterator

SUPPORTED_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}


def find(source: Path) -> Iterator[Path]:
    """Find supported font files from a file or recursively from a directory."""
    source = source.resolve()

    if source.is_file():
        if source.suffix.lower() in SUPPORTED_FONT_EXTENSIONS:
            yield source
        return

    if not source.exists():
        raise FileNotFoundError(f"source does not exist: {source}")

    if not source.is_dir():
        raise ValueError(f"source is not a file or directory: {source}")

    for path in sorted(source.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_FONT_EXTENSIONS:
            yield path
