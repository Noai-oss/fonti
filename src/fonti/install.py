import shutil
import sys
import winreg
from collections.abc import Generator, Iterable, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import ClassVar, Literal

from fonti.ls import find_installed_fonts
from fonti.meta import reg_name
from fonti.scan import find
from fonti.sources import local_source
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


@dataclass(frozen=True)
class InstallResult:
    path: Path
    name: str
    status: Literal["installed", "skipped"]
    message: str = ""


@dataclass(frozen=True)
class FailedInstall:
    path: Path
    error: OSError | ValueError
    status: ClassVar[Literal["failed"]] = "failed"

    @property
    def message(self) -> str:
        return str(self.error)


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


def activation_warning(target: Path) -> str:
    try:
        if add_font_resource(target):
            return ""
        return f"Immediate activation failed for '{target}'; a restart may be required."
    except OSError as exc:
        return f"Immediate activation failed for '{target}': {exc}. A restart may be required."


def install_one(source: Path, *, system: bool, replace: bool) -> InstallResult:
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
        return InstallResult(source, name, "skipped")
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

    warning = "" if other_names else activation_warning(target)
    return InstallResult(source, name, "installed", warning)


def install_files(
    files: Iterable[Path], *, system: bool = False, replace: bool = False
) -> Generator[InstallResult | FailedInstall]:
    """Install these exact files in order, stopping at the first failed result."""
    if system and not is_admin():
        raise ValueError("Installing system fonts requires administrator privileges.")
    if not system and get_windows_build_number() < WIN10_1809_BUILD:
        raise ValueError("User fonts require Windows 10 version 1809 or later.")

    changed = False
    try:
        for source in files:
            try:
                result = install_one(source, system=system, replace=replace)
            except OSError as exc:
                yield FailedInstall(
                    source, OSError(f"Could not install '{source}': {exc}")
                )
                return
            except ValueError as exc:
                yield FailedInstall(source, exc)
                return
            changed = changed or result.status == "installed"
            yield result
    finally:
        if changed:
            broadcast_font_change()


def _source_files(paths: Sequence[str | Path]) -> Generator[Path]:
    for path in paths:
        found = False
        with local_source(path) as local:
            for source in find(local):
                found = True
                yield source
        if not found:
            raise ValueError(f"No supported fonts in '{path}'.")


def install(
    paths: Sequence[str | Path], *, system: bool = False, replace: bool = False
) -> None:
    with (
        closing(_source_files(paths)) as files,
        closing(install_files(files, system=system, replace=replace)) as results,
    ):
        for result in results:
            if isinstance(result, FailedInstall):
                raise result.error
            label = "Installed" if result.status == "installed" else "Already installed"
            print(f"{label}: {result.name}")
            if result.message:
                print(f"Warning: {result.message}", file=sys.stderr)
