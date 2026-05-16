from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path


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
