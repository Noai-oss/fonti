from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from fonti.win.reg import iter_font_registry_values, resolve_registry_font_path


class InstalledFont(NamedTuple):
    name: str
    registry_value: str
    path: Path


def find_installed_fonts(
    is_global: bool = False, keyword: str = ""
) -> Iterator[InstalledFont]:
    text = keyword.casefold()
    for name, value, _ in iter_font_registry_values(is_global):
        if not isinstance(value, str) or not value:
            continue
        path = resolve_registry_font_path(value, is_global)
        if text in name.casefold() or text in path.name.casefold():
            yield InstalledFont(name, value, path)


def list_installed_fonts(is_global: bool = False, keyword: str = "") -> None:
    for font in find_installed_fonts(is_global, keyword):
        print(f"{font.name}\t{font.path.name}")
