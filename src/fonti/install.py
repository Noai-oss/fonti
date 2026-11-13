import shutil
import sys
import winreg
from collections.abc import Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile

from fonti.ls import find_installed_fonts
from fonti.meta import reg_name
from fonti.scan import find
from fonti.win.active import (
    add_font_resource,
    broadcast_font_change,
    remove_font_resource,
)
from fonti.win.env import WIN10_1809_BUILD, get_windows_build_number, is_admin
from fonti.win.reg import (
    FONT_REGISTRY_PATH,
    get_font_install_dir,
    get_registry_root,
    get_registry_value_data,
)


def same_contents(source: Path, target: Path) -> bool:
    if source.samefile(target):
        return True
    if source.stat().st_size != target.stat().st_size:
        return False
    with source.open("rb") as left, target.open("rb") as right:
        while chunk := left.read(1024 * 1024):
            if chunk != right.read(len(chunk)):
                return False
        return not right.read(1)


def copy_font(source: Path, target: Path, *, overwrite: bool, registered: bool) -> None:
    # Publish a complete file so an interrupted copy can be retried.
    with NamedTemporaryFile(dir=target.parent, delete=False) as temp:
        staged = Path(temp.name)
    try:
        shutil.copyfile(source, staged)
        deactivated = overwrite and registered and remove_font_resource(target)
        try:
            if overwrite:
                staged.replace(target)
            else:
                # On Windows rename fails if another process created the destination.
                staged.rename(target)
        except OSError:
            if deactivated:
                add_font_resource(target)
            raise
    finally:
        staged.unlink(missing_ok=True)


def install_one(source: Path, *, system: bool, replace: bool) -> bool:
    name = reg_name(source)
    target = get_font_install_dir(system) / source.name
    registered = False
    other_names = []
    for font in find_installed_fonts(system):
        if font.name.casefold() == name.casefold():
            if font.path != target:
                raise ValueError(
                    f"'{name}' already points to '{font.path}'. Remove that entry first."
                )
            registered = True
        elif font.path == target:
            other_names.append(font.name)

    exists = target.exists()
    identical = exists and same_contents(source, target)
    if identical and registered:
        print(f"Already installed: {name}")
        return False
    if exists and not identical and not replace:
        raise ValueError(
            f"Different contents at '{target}'. Use --replace to overwrite."
        )
    if not identical and other_names:
        raise ValueError(
            f"'{target}' is registered as {', '.join(other_names)}. Remove the conflicting entries first."
        )

    with winreg.CreateKeyEx(
        get_registry_root(system), FONT_REGISTRY_PATH, 0, winreg.KEY_SET_VALUE
    ) as key:
        if not identical:
            target.parent.mkdir(parents=True, exist_ok=True)
            copy_font(source, target, overwrite=exists, registered=registered)
        if not registered:
            winreg.SetValueEx(
                key, name, 0, winreg.REG_SZ, get_registry_value_data(target, system)
            )

    print(f"Installed: {name}")
    if not other_names:
        try:
            if not add_font_resource(target):
                print(
                    f"Warning: Immediate activation failed for '{target}'; a restart may be required.",
                    file=sys.stderr,
                )
        except OSError as exc:
            print(
                f"Warning: Immediate activation failed for '{target}': {exc}. A restart may be required.",
                file=sys.stderr,
            )
    return True


def install(
    paths: Sequence[Path], *, system: bool = False, replace: bool = False
) -> None:
    if system and not is_admin():
        raise ValueError("Installing system fonts requires administrator privileges.")
    if not system and get_windows_build_number() < WIN10_1809_BUILD:
        raise ValueError("User fonts require Windows 10 version 1809 or later.")

    changed = False
    try:
        for path in paths:
            found = False
            for source in find(path):
                found = True
                try:
                    if install_one(source, system=system, replace=replace):
                        changed = True
                except OSError as exc:
                    raise OSError(f"Could not install '{source}': {exc}") from exc
            if not found:
                raise ValueError(f"No supported fonts in '{path}'.")
    finally:
        if changed:
            broadcast_font_change()
