from __future__ import annotations

from pathlib import Path

from fonti.meta import kind, reg_name
from fonti.scan import find
from fonti.sources import is_https, local_source


def show_info(source: str | Path) -> None:
    """Show metadata from a font source and print the calculated registry name."""
    any_found = False

    with local_source(source) as path:
        for font_file in find(path):
            any_found = True
            label = font_file
            if is_https(source):
                label = font_file.relative_to(path if path.is_dir() else path.parent)
            print(label)
            print(f"  Registry name: {reg_name(font_file)}")
            print(f"  Kind: {kind(font_file)}")

    if not any_found:
        print(f"No supported font files found in: {source}")
