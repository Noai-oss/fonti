from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from fonti.meta import kind, reg_name
from fonti.scan import find
from fonti.sources import is_https, local_source


class FontInfo(NamedTuple):
    path: Path
    name: str
    kind: str


class FailedScan(NamedTuple):
    path: Path
    error: OSError | ValueError


def scan_fonts(source: Path) -> Iterator[FontInfo | FailedScan]:
    for path in find(source):
        try:
            row = FontInfo(path, reg_name(path), kind(path))
        except (OSError, ValueError) as exc:
            row = FailedScan(path, exc)
        yield row


def show_info(source: str | Path) -> None:
    """Show metadata from a font source and print the calculated registry name."""
    any_found = False

    with local_source(source) as path:
        for font in scan_fonts(path):
            any_found = True
            label = font.path
            if is_https(source):
                label = font.path.relative_to(path if path.is_dir() else path.parent)
            print(label)
            if isinstance(font, FailedScan):
                raise font.error
            print(f"  Registry name: {font.name}")
            print(f"  Kind: {font.kind}")

    if not any_found:
        print(f"No supported font files found in: {source}")
