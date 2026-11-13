import sys
import winreg
from collections import Counter
from collections.abc import Sequence

from fonti.ls import InstalledFont, find_installed_fonts
from fonti.win.active import (
    add_font_resource,
    broadcast_font_change,
    remove_font_resource,
)
from fonti.win.env import is_admin
from fonti.win.reg import (
    FONT_REGISTRY_PATH,
    get_font_install_dir,
    get_registry_root,
    resolve_registry_font_path,
)


def resolve_targets(
    tokens: Sequence[str], installed: list[InstalledFont]
) -> list[InstalledFont]:
    selected = {}
    for token in tokens:
        exact = token.casefold()
        matches = [
            font
            for font in installed
            if exact in (font.name.casefold(), font.path.name.casefold())
        ]
        if not matches:
            raise ValueError(f"No installed font matched '{token}'.")
        if len(matches) > 1:
            names = ", ".join(font.name for font in matches)
            raise ValueError(
                f"Ambiguous target '{token}' matches: {names}. Use an exact installed name."
            )
        font = matches[0]
        selected[font.name] = font
    return list(selected.values())


def remove(tokens: Sequence[str], *, system: bool = False) -> None:
    if system and not is_admin():
        raise ValueError("Removing system fonts requires administrator privileges.")
    installed = list(find_installed_fonts(system))
    targets = resolve_targets(tokens, installed)
    directory = get_font_install_dir(system).resolve()
    references = Counter(font.path.resolve() for font in installed)
    changed = False
    try:
        with winreg.OpenKey(
            get_registry_root(system),
            FONT_REGISTRY_PATH,
            0,
            winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE,
        ) as key:
            for font in targets:
                path = font.path.resolve()
                try:
                    value, value_type = winreg.QueryValueEx(key, font.name)
                    if (
                        not isinstance(value, str)
                        or resolve_registry_font_path(value, system).resolve() != path
                    ):
                        raise ValueError(
                            f"Registration for '{font.name}' changed. Run 'fonti list' again."
                        )
                    winreg.DeleteValue(key, font.name)
                except OSError as exc:
                    raise OSError(
                        f"Could not remove registration for '{font.name}': {exc}"
                    ) from exc
                deactivated = False
                try:
                    if references[path] == 1 and path.exists():
                        deactivated = remove_font_resource(path)
                        if (
                            path.parent == directory
                            and font.path.parent.resolve() == directory
                        ):
                            font.path.unlink()
                        if not deactivated:
                            print(
                                f"Warning: Immediate deactivation failed for '{font.name}'; a restart may be required.",
                                file=sys.stderr,
                            )
                except OSError as exc:
                    winreg.SetValueEx(key, font.name, 0, value_type, value)
                    if deactivated:
                        add_font_resource(path)
                    raise OSError(
                        f"Could not remove '{font.name}' at '{path}': {exc}"
                    ) from exc
                references[path] -= 1
                changed = True
                print(f"Removed: {font.name}")
    finally:
        if changed:
            broadcast_font_change()
