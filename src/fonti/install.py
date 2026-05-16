from __future__ import annotations

import shutil
import winreg
from pathlib import Path

from fonti.meta import reg_name
from fonti.scan import find
from fonti.select import select
from fonti.win.env import (
    WIN10_1809_BUILD,
    get_windows_build_number,
    is_admin,
)
from fonti.win.active import add_font_resource, broadcast_font_change
from fonti.win.reg import (
    FONT_REGISTRY_PATH,
    get_font_install_dir,
    get_registry_root,
    get_registry_value_data,
)


def install(
    source: Path,
    is_global: bool = False,
    force: bool = False,
    name_regex: str | None = None,
    formats: list[str] | None = None,
) -> None:
    """Copy fonts, register them in Windows, and broadcast the update."""
    build_number = get_windows_build_number()

    if build_number < WIN10_1809_BUILD and not is_global:
        raise SystemExit(
            f"Error: Windows Build {build_number} is too old for user-level fonts. "
            f"User-level fonts require Windows 10 Version 1809 or later."
        )

    if is_global and not is_admin():
        raise SystemExit("Error: Global font installation requires admin privileges.")

    font_install_dir = get_font_install_dir(is_global)
    registry_root = get_registry_root(is_global)

    if not is_global:
        font_install_dir.mkdir(parents=True, exist_ok=True)

    font_files = select(
        find(source),
        name_regex=name_regex,
        formats=formats,
    )

    any_installed = False

    with winreg.CreateKeyEx(
        registry_root,
        FONT_REGISTRY_PATH,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        for font_file in font_files:
            any_installed = True
            font_file = font_file.resolve()
            font_name = reg_name(font_file)
            target_path = font_install_dir / font_file.name

            same_file = False
            try:
                same_file = font_file.samefile(target_path)
            except FileNotFoundError:
                same_file = False

            if not same_file:
                if target_path.exists() and not force:
                    print(f"Skip existing file: {target_path}")
                    continue

                shutil.copy2(font_file, target_path)

            registry_value = get_registry_value_data(target_path, is_global)
            winreg.SetValueEx(key, font_name, 0, winreg.REG_SZ, registry_value)

            added = add_font_resource(target_path)
            print(f"Installed persistently: {font_name}")
            print(f"  File: {target_path}")
            print(f"  Registry: {registry_value}")

            if added == 0:
                print("  Immediate activation: failed; reboot may be required.")
            else:
                print(f"  Immediate activation: ok ({added})")

    if not any_installed:
        print(f"No valid/matching font files found in: {source}")
        return

    broadcast_font_change()
