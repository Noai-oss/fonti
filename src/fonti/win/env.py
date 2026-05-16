from __future__ import annotations

import ctypes
import winreg

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
