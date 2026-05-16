from __future__ import annotations

import re
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


def normalize_formats(formats: list[str] | None = None) -> set[str]:
    """Normalize parsed font formats for filtering."""
    if formats:
        return {font_format.casefold().removeprefix(".") for font_format in formats}

    return set()


def compile_name_regex(name_regex: str) -> re.Pattern[str]:
    """Compile a case-insensitive name regex with a CLI-friendly error."""
    try:
        return re.compile(name_regex, re.IGNORECASE)
    except re.error as exc:
        raise SystemExit(f"Error: Invalid --name-regex: {exc}") from exc


def list_installed_fonts(
    is_global: bool = False,
    name_regex: str | None = None,
) -> None:
    """Print a list of installed fonts for the defined scope and filters."""
    scope = "global" if is_global else "user"
    print(f"Scope: {scope}")
    print("-" * 100)

    matches = get_installed_font_matches(
        is_global=is_global,
        name_regex=name_regex,
    )

    if not matches:
        print("No installed fonts matched.")
        return

    for name, value, _ in matches:
        print(f"{name} | {value}")


def filter_font_files(
    font_files: list[Path],
    name_regex: str | None = None,
    formats: list[str] | None = None,
) -> list[Path]:
    """Filter font files by extension and file/registry name."""
    allowed_formats = normalize_formats(formats)

    if allowed_formats:
        font_files = [
            font_file
            for font_file in font_files
            if font_file.suffix.casefold().removeprefix(".") in allowed_formats
        ]

    if not name_regex:
        return font_files

    pattern = compile_name_regex(name_regex)

    return [
        font_file
        for font_file in font_files
        if pattern.search(font_file.name)
        or pattern.search(get_font_registry_name(font_file))
    ]


def get_installed_font_matches(
    is_global: bool = False,
    name_regex: str | None = None,
) -> list[tuple[str, str, Path]]:
    """Return installed fonts matching registry name filters."""
    pattern = compile_name_regex(name_regex) if name_regex else None
    matches: list[tuple[str, str, Path]] = []

    for name, value, _ in iter_font_registry(is_global):
        installed_path = get_abs_registry_font_path(value, is_global)

        if pattern and not pattern.search(name):
            continue

        matches.append((name, value, installed_path))

    return matches


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


def uninstall_font_matches(matches: list[tuple[str, Path]], is_global: bool) -> None:
    """Uninstall pre-matched registry names and font files."""
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


def install_fonts(
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
    reg_root = get_reg_root(is_global)

    if not is_global:
        font_install_dir.mkdir(parents=True, exist_ok=True)

    font_files = get_font_files(source)

    if not font_files:
        print(f"No supported font files found in: {source}")
        return

    font_files = filter_font_files(font_files, name_regex=name_regex, formats=formats)

    if not font_files:
        print(f"No fonts matched filters in: {source}")
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

    uninstall_font_matches(matches, is_global)


def uninstall_by_filters(
    name_regex: str | None = None,
    is_global: bool = False,
) -> None:
    """Uninstall installed fonts matching registry name filters."""
    if not name_regex:
        raise SystemExit("Error: uninstall filters require --name-regex.")

    matched_fonts = get_installed_font_matches(
        is_global=is_global,
        name_regex=name_regex,
    )
    matches = [(name, installed_path) for name, _, installed_path in matched_fonts]

    if not matches:
        raise SystemExit("No installed fonts matched filters.")

    uninstall_font_matches(matches, is_global)
