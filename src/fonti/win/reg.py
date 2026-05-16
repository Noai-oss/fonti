from __future__ import annotations

import os
import winreg
from collections.abc import Iterator
from pathlib import Path

FONT_REGISTRY_PATH = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"


def get_registry_root(is_global: bool) -> int:
    """Return the registry root HKEY based on the installation scope."""
    return winreg.HKEY_LOCAL_MACHINE if is_global else winreg.HKEY_CURRENT_USER


def get_font_install_dir(is_global: bool) -> Path:
    """Return the target directory for font installation based on scope."""
    if is_global:
        return Path(os.environ["WINDIR"]) / "Fonts"

    return Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"


def get_registry_value_data(target_path: Path, is_global: bool) -> str:
    """Determine the registry value data to write for a target font file."""
    if is_global:
        return target_path.name

    return str(target_path)


def resolve_registry_font_path(value: str, is_global: bool) -> Path:
    """Resolve a registry value data string back to an absolute path."""
    path = Path(value)

    if path.is_absolute():
        return path

    return get_font_install_dir(is_global) / value


def iter_font_registry_values(is_global: bool) -> Iterator[tuple[str, str, int]]:
    """Yield all value entries from the Windows font registry key."""
    registry_root = get_registry_root(is_global)

    try:
        with winreg.OpenKey(registry_root, FONT_REGISTRY_PATH) as key:
            count = winreg.QueryInfoKey(key)[1]

            for index in range(count):
                name, value, value_type = winreg.EnumValue(key, index)
                yield name, value, value_type
    except FileNotFoundError:
        return
