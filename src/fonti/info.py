from __future__ import annotations

from pathlib import Path

from fonti.meta import kind, reg_name
from fonti.scan import find


def show_info(source: Path) -> None:
    """Show metadata from a font source and print the calculated registry name."""
    any_found = False

    for font_file in find(source):
        any_found = True
        print(f"{font_file}")
        print(f"  Registry name: {reg_name(font_file)}")
        print(f"  Kind: {kind(font_file)}")

    if not any_found:
        print(f"No supported font files found in: {source}")
