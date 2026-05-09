import ctypes
import os
import sys
import winreg
import shutil
from pathlib import Path
import win32security
import ntsecuritycon as con
from fontTools.ttLib import TTFont
import argparse


if sys.platform != "win32":
    print("Error: This tool is only supported on Windows.")
    sys.exit(1)

FONT_REG_PATH = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
WIN10_1809_BUILD = 17763


def font_kind(path: Path) -> str:
    match path.suffix.lower():
        case ".ttf":
            return "TrueType"
        case ".otf":
            return "OpenType"
        case _:
            raise ValueError(f"unsupported font type: {path}")


def get_font_registry_name(font_path: Path) -> str:
    with TTFont(font_path, fontNumber=0) as font:
        name = font["name"]

        family = name.getBestFamilyName()
        subfamily = name.getBestSubFamilyName()
        full_name = name.getBestFullName()

    kind = font_kind(font_path)
    if family:
        if subfamily:
            return f"{family} {subfamily} ({kind})"
        else:
            return f"{family} ({kind})"
    if full_name:
        return f"{full_name} ({kind})"

    return f"{font_path.stem} ({kind})"


def get_windows_build_number() -> int:
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
    ) as key:
        return int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def add_font_resource(font_path: Path) -> int:
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    return int(gdi32.AddFontResourceW(str(font_path)))


def broadcast_font_change() -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    HWND_BROADCAST = 0xFFFF
    WM_FONTCHANGE = 0x001D
    SMTO_ABORTIFHUNG = 0x0002

    result = ctypes.c_void_p()

    user32.SendMessageTimeoutW(
        HWND_BROADCAST,
        WM_FONTCHANGE,
        0,
        0,
        SMTO_ABORTIFHUNG,
        1000,
        ctypes.byref(result),
    )


def get_font_files(source_dir: Path) -> list[Path]:
    extensions = ("*.ttf", "*.otf")

    return [p for ext in extensions for p in source_dir.rglob(ext) if p.is_file()]


def get_reg_root(is_global: bool = False) -> int:
    if is_global:
        return winreg.HKEY_LOCAL_MACHINE
    else:
        return winreg.HKEY_CURRENT_USER


def get_font_install_dir(is_global: bool = False) -> Path:
    if is_global:
        return Path(os.environ["windir"]) / "Fonts"
    else:
        return Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"


def install_font(source_dir: Path, is_global: bool = False) -> None:
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"source dir does not exist: {source_dir}")
    build_number = get_windows_build_number()
    print(f"Windows Build: {build_number}")

    if build_number < WIN10_1809_BUILD and not is_global:
        print(
            f"Error: Windows Build {build_number} is too old for user-level fonts. "
            f"User-level fonts require Windows 10 Version 1809 or later."
        )
        sys.exit(1)

    font_install_dir = get_font_install_dir(is_global)
    reg_root = get_reg_root(is_global)

    if is_global:
        if not is_admin():
            print("Error: Global font installation requires admin privileges.")
            sys.exit(1)
    else:
        font_install_dir.mkdir(parents=True, exist_ok=True)

    font_files = get_font_files(source_dir)
    if not font_files:
        print(f"No .ttf or .otf font files found in: {source_dir}")
        return

    with winreg.CreateKeyEx(reg_root, FONT_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        for font_file in font_files:
            font_name = get_font_registry_name(font_file)
            target_path = font_install_dir / font_file.name

            if font_file.resolve() != target_path.resolve():
                shutil.copy2(font_file, target_path)

            if is_global:
                reg_value = target_path.name
            else:
                reg_value = str(target_path)

            winreg.SetValueEx(
                key,
                font_name,
                0,
                winreg.REG_SZ,
                reg_value,
            )

            added = add_font_resource(target_path)

            print(f"Installed: {font_name} = {reg_value}")
            print(f"AddFontResourceW: {added}")

    broadcast_font_change()


def set_font_dir_permissions(font_dir: Path) -> None:
    sd = win32security.GetFileSecurity(
        str(font_dir), win32security.DACL_SECURITY_INFORMATION
    )
    dacl = sd.GetSecurityDescriptorDacl()
    if dacl is None:
        dacl = win32security.ACL()

    # S-1-15-2-1: ALL APPLICATION PACKAGES
    # S-1-15-2-2: ALL RESTRICTED APPLICATION PACKAGES
    sids = ["S-1-15-2-1", "S-1-15-2-2"]

    perms = con.FILE_GENERIC_READ | con.FILE_GENERIC_EXECUTE

    inheritance = win32security.SUB_CONTAINERS_AND_OBJECTS_INHERIT

    for sid_str in sids:
        sid = win32security.ConvertStringSidToSid(sid_str)
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, inheritance, perms, sid)
    sd.SetSecurityDescriptorDacl(1, dacl, 0)
    win32security.SetFileSecurity(
        str(font_dir), win32security.DACL_SECURITY_INFORMATION, sd
    )
    print(f"Permissions applied to: {font_dir}")


def list_installed_fonts(is_global: bool = False) -> None:
    reg_root = get_reg_root(is_global)

    with winreg.OpenKey(reg_root, FONT_REG_PATH) as key:
        count = winreg.QueryInfoKey(key)[1]
        for i in range(count):
            name, value, _ = winreg.EnumValue(key, i)
            print(f"{name:40} | {value}")


def uninstall_font(font_name_to_remove: str, is_global: bool = False) -> None:
    reg_root = get_reg_root(is_global)
    font_install_dir = get_font_install_dir(is_global)
    with winreg.OpenKey(reg_root, FONT_REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
        full_path_str, _ = winreg.QueryValueEx(key, font_name_to_remove)
        full_path = (
            font_install_dir / full_path_str
            if not Path(full_path_str).is_absolute()
            else Path(full_path_str)
        )

        winreg.DeleteValue(key, font_name_to_remove)

        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        gdi32.RemoveFontResourceW(str(full_path))

        if full_path.exists():
            full_path.unlink()

        print(f"Uninstalled: {font_name_to_remove}")

    broadcast_font_change()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fonti", description="A command-line tool for installing fonts on Windows"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # install subcommand
    install_parser = subparsers.add_parser("install", help="Install fonts")
    install_parser.add_argument(
        "source_dir", type=Path, help="Source directory containing font files"
    )
    install_parser.add_argument(
        "--global",
        action="store_true",
        dest="is_global",  # Map '--global' flag to 'is_global' attribute
    )

    # uninstall subcommand
    uninstall_parser = subparsers.add_parser(
        "uninstall", help="Uninstall a font by its registry name"
    )
    uninstall_parser.add_argument(
        "name",
        help="The full name in registry, e.g., 'Agave Nerd Font Mono Bold (TrueType)'",
    )
    uninstall_parser.add_argument("--global", action="store_true", dest="is_global")

    list_parser = subparsers.add_parser("list", help="List installed fonts")
    list_parser.add_argument("--global", action="store_true", dest="is_global")
    args = parser.parse_args()

    match args.command:
        case "install":
            install_font(args.source_dir, is_global=args.is_global)
        case "uninstall":
            uninstall_font(args.name, is_global=args.is_global)
        case "list":
            list_installed_fonts(is_global=args.is_global)
        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
