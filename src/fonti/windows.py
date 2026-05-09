from __future__ import annotations

import ctypes
import os
import winreg
from ctypes import wintypes
from pathlib import Path

FONT_REG_PATH = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
WIN10_1809_BUILD = 17763


def get_windows_build_number() -> int:
    """Retrieve the current Windows build number from the registry."""
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
    ) as key:
        return int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])


def is_admin() -> bool:
    """Check if the current process has administrative privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def get_reg_root(is_global: bool) -> int:
    """Return the registry root HKEY based on the installation scope."""
    return winreg.HKEY_LOCAL_MACHINE if is_global else winreg.HKEY_CURRENT_USER


def get_font_install_dir(is_global: bool) -> Path:
    """Return the target directory for font installation based on scope."""
    if is_global:
        return Path(os.environ["WINDIR"]) / "Fonts"

    return Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"


def get_reg_value(target_path: Path, is_global: bool) -> str:
    """Determine the registry value to write (relative or absolute path)."""
    if is_global:
        return target_path.name

    return str(target_path)


def get_abs_registry_font_path(value: str, is_global: bool) -> Path:
    """Resolve a registry value back to an absolute Path object."""
    path = Path(value)

    if path.is_absolute():
        return path

    return get_font_install_dir(is_global) / value


def add_font_resource(font_path: Path) -> int:
    """Register a font file with the Windows GDI."""
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    AddFontResourceW = gdi32.AddFontResourceW
    AddFontResourceW.argtypes = [wintypes.LPCWSTR]
    AddFontResourceW.restype = ctypes.c_int

    return int(AddFontResourceW(str(font_path)))


def remove_font_resource(font_path: Path) -> bool:
    """Unregister a font file from the Windows GDI."""
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    RemoveFontResourceW = gdi32.RemoveFontResourceW
    RemoveFontResourceW.argtypes = [wintypes.LPCWSTR]
    RemoveFontResourceW.restype = wintypes.BOOL

    return bool(RemoveFontResourceW(str(font_path)))


def broadcast_font_change() -> None:
    """Broadcast the WM_FONTCHANGE message to running applications."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    HWND_BROADCAST = 0xFFFF
    WM_FONTCHANGE = 0x001D
    SMTO_ABORTIFHUNG = 0x0002

    DWORD_PTR = wintypes.WPARAM
    result = DWORD_PTR()

    SendMessageTimeoutW = user32.SendMessageTimeoutW
    SendMessageTimeoutW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.POINTER(DWORD_PTR),
    ]
    SendMessageTimeoutW.restype = wintypes.LPARAM

    ret = SendMessageTimeoutW(
        HWND_BROADCAST,
        WM_FONTCHANGE,
        0,
        0,
        SMTO_ABORTIFHUNG,
        1000,
        ctypes.byref(result),
    )

    if ret == 0:
        error = ctypes.get_last_error()
        if error:
            print(f"Warning: WM_FONTCHANGE broadcast failed: {ctypes.WinError(error)}")


def iter_font_registry(is_global: bool):
    """Yield all entries from the Windows Font registry key."""
    reg_root = get_reg_root(is_global)

    try:
        with winreg.OpenKey(reg_root, FONT_REG_PATH) as key:
            count = winreg.QueryInfoKey(key)[1]

            for index in range(count):
                name, value, value_type = winreg.EnumValue(key, index)
                yield name, value, value_type
    except FileNotFoundError:
        return
