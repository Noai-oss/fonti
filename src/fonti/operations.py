from __future__ import annotations

import shutil
import winreg
from pathlib import Path

from fonti.windows import (
    WIN10_1809_BUILD,
    FONT_REG_PATH,
    get_windows_build_number,
    is_admin,
    get_font_install_dir,
    get_reg_root,
    get_reg_value,
    get_abs_registry_font_path,
    iter_font_registry,
    add_font_resource,
    remove_font_resource,
    broadcast_font_change,
)
from fonti.font import (
    get_font_files,
    get_font_registry_name,
    get_font_kind,
)


def inspect_fonts(source: Path) -> None:
    """Read metadata from a font source and print the calculated registry name."""
    font_files = get_font_files(source)

    if not font_files:
        print(f"No supported font files found in: {source}")
        return

    for font_file in font_files:
        print(f"{font_file}")
        print(f"  Registry name: {get_font_registry_name(font_file)}")
        print(f"  Kind: {get_font_kind(font_file)}")


def list_installed_fonts(is_global: bool = False) -> None:
    """Print a list of all currently installed fonts for the defined scope."""
    scope = "global" if is_global else "user"
    print(f"Scope: {scope}")
    print("-" * 100)

    for name, value, _ in iter_font_registry(is_global):
        print(f"{name} | {value}")


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


def install_fonts(source: Path, is_global: bool = False, force: bool = False) -> None:
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
    reg_root = get_reg_root(is_global)

    if not is_global:
        font_install_dir.mkdir(parents=True, exist_ok=True)

    font_files = get_font_files(source)

    if not font_files:
        print(f"No supported font files found in: {source}")
        return

    with winreg.CreateKeyEx(reg_root, FONT_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        for font_file in font_files:
            font_file = font_file.resolve()
            font_name = get_font_registry_name(font_file)
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
                else:
                    shutil.copy2(font_file, target_path)

            reg_value = get_reg_value(target_path, is_global)

            winreg.SetValueEx(
                key,
                font_name,
                0,
                winreg.REG_SZ,
                reg_value,
            )

            added = add_font_resource(target_path)
            print(f"Installed persistently: {font_name}")
            print(f"  File: {target_path}")
            print(f"  Registry: {reg_value}")

            if added == 0:
                print("  Immediate activation: failed; reboot may be required.")
            else:
                print(f"  Immediate activation: ok ({added})")

    broadcast_font_change()


def uninstall_by_registry_name(font_name: str, is_global: bool = False) -> None:
    """Uninstall a font identified by its exact Windows registry value name."""
    reg_root = get_reg_root(is_global)

    try:
        with winreg.OpenKey(reg_root, FONT_REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
            reg_value, _ = winreg.QueryValueEx(key, font_name)
            font_path = get_abs_registry_font_path(reg_value, is_global)

            ensure_font_file_removable(font_path, font_name)
            remove_font_resource(font_path)
            winreg.DeleteValue(key, font_name)

            if font_path.exists():
                font_path.unlink()

            print(f"Uninstalled: {font_name}")
            print(f"  File: {font_path}")
    except FileNotFoundError:
        raise SystemExit(
            f"Error: No installed font found with registry name: {font_name}"
        )

    broadcast_font_change()


def uninstall_by_file(file: Path, is_global: bool = False) -> None:
    """Uninstall fonts matching a given file name or absolute path."""
    file_token = str(file)
    file_path = Path(file_token)

    if file_path.is_absolute():
        target_path = file_path.resolve()
    else:
        if file_path.name != file_token or not file_path.suffix:
            raise SystemExit(
                "Error: --file must be an absolute path or a file name with extension."
            )

        target_path = get_font_install_dir(is_global) / file_path.name

    matches: list[tuple[str, Path]] = []

    for name, value, _ in iter_font_registry(is_global):
        installed_path = get_abs_registry_font_path(value, is_global)

        matched = (
            installed_path.resolve().as_posix().casefold()
            == target_path.resolve().as_posix().casefold()
        )

        if matched:
            matches.append((name, installed_path))

    if not matches:
        raise SystemExit(f"No installed font matched file: {file}")

    for name, installed_path in matches:
        ensure_font_file_removable(installed_path, name)

    reg_root = get_reg_root(is_global)

    with winreg.OpenKey(reg_root, FONT_REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
        for name, installed_path in matches:
            remove_font_resource(installed_path)
            winreg.DeleteValue(key, name)

            if installed_path.exists():
                installed_path.unlink()

            print(f"Uninstalled: {name}")
            print(f"  File: {installed_path}")

    broadcast_font_change()
