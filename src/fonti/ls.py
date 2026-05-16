from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from fonti.select import compile_name_regex
from fonti.win.reg import (
    iter_font_registry_values,
    resolve_registry_font_path,
)


class InstalledFont(NamedTuple):
    """A font entry installed in the Windows font registry."""

    name: str
    registry_value: str
    path: Path


def find_installed_fonts(
    is_global: bool = False,
    name_regex: str | None = None,
) -> Iterator[InstalledFont]:
    """Return installed fonts matching registry name filters."""
    pattern = compile_name_regex(name_regex) if name_regex else None

    for name, value, _ in iter_font_registry_values(is_global):
        installed_path = resolve_registry_font_path(value, is_global)

        if pattern and not pattern.search(name):
            continue

        yield InstalledFont(name, value, installed_path)


def list_installed_fonts(
    is_global: bool = False,
    name_regex: str | None = None,
) -> None:
    """Print a list of installed fonts for the defined scope and filters."""
    for font in find_installed_fonts(is_global=is_global, name_regex=name_regex):
        print(f"{font.name}\t{font.registry_value}\t{font.path}")
