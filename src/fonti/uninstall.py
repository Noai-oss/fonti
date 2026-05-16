from __future__ import annotations

import winreg
from pathlib import Path
from typing import NamedTuple

from fonti.ls import find_installed_fonts
from fonti.win.active import broadcast_font_change, remove_font_resource
from fonti.win.reg import (
    FONT_REGISTRY_PATH,
    get_font_install_dir,
    get_registry_root,
    iter_font_registry_values,
    resolve_registry_font_path,
)


from collections.abc import Iterable


class UninstallTarget(NamedTuple):
    """A resolved registry name and font file to uninstall together."""

    name: str
    path: Path


def ensure_font_file_removable(font_path: Path, font_name: str) -> None:
    """Fail before registry changes if Windows still has the font file locked."""
    if not font_path.exists():
        return

    try:
        font_path.rename(font_path)
    except OSError as exc:
        raise SystemExit(
            f"Error: Cannot uninstall '{font_name}' because the font file is in use.\n"
            f"File: {font_path}\n"
            "Close applications that are using this font, then try again."
        ) from exc


def uninstall_font_targets(
    targets: Iterable[UninstallTarget],
    is_global: bool,
) -> None:
    """Uninstall pre-resolved registry names and font files."""
    targets = list(targets)
    if not targets:
        return

    for target in targets:
        ensure_font_file_removable(target.path, target.name)

    registry_root = get_registry_root(is_global)

    with winreg.OpenKey(
        registry_root,
        FONT_REGISTRY_PATH,
        0,
        winreg.KEY_ALL_ACCESS,
    ) as key:
        for target in targets:
            remove_font_resource(target.path)
            winreg.DeleteValue(key, target.name)

            if target.path.exists():
                target.path.unlink()

            print(f"Uninstalled: {target.name}")
            print(f"  File: {target.path}")

    broadcast_font_change()


def resolve_uninstall_target(
    token: str, is_global: bool = False
) -> Iterable[UninstallTarget]:
    file_path = Path(token)

    # Try treating as file if it has an extension or is an absolute path
    if file_path.is_absolute() or (file_path.name == token and file_path.suffix):
        if file_path.is_absolute():
            target_path = file_path.resolve()
        else:
            target_path = get_font_install_dir(is_global) / file_path.name

        target_value = target_path.resolve().as_posix().casefold()
        found = False

        for name, value, _ in iter_font_registry_values(is_global):
            installed_path = resolve_registry_font_path(value, is_global)
            if installed_path.resolve().as_posix().casefold() == target_value:
                found = True
                yield UninstallTarget(name, installed_path)

        if found:
            return

    # Treat as registry name
    registry_root = get_registry_root(is_global)
    try:
        with winreg.OpenKey(
            registry_root, FONT_REGISTRY_PATH, 0, winreg.KEY_READ
        ) as key:
            registry_value, _ = winreg.QueryValueEx(key, token)
            font_path = resolve_registry_font_path(registry_value, is_global)
            yield UninstallTarget(token, font_path)
    except FileNotFoundError:
        pass


def uninstall_by_filters(
    name_regex: str | None = None,
    is_global: bool = False,
) -> None:
    """Uninstall installed fonts matching registry name filters."""
    if not name_regex:
        raise SystemExit("Error: uninstall filters require --name-regex.")

    def _iter_targets() -> Iterable[UninstallTarget]:
        for font in find_installed_fonts(is_global=is_global, name_regex=name_regex):
            yield UninstallTarget(font.name, font.path)

    targets = list(_iter_targets())
    if not targets:
        raise SystemExit("No installed fonts matched filters.")

    uninstall_font_targets(targets, is_global)
