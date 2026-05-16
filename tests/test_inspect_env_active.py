from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import fonti.inspect as inspect_module
import fonti.win.active as active_module
import fonti.win.env as env_module


class FakeRegistryKey:
    def __enter__(self) -> "FakeRegistryKey":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class FakeWinFunction:
    def __init__(self, return_value: object) -> None:
        self.return_value = return_value
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *args: object) -> object:
        self.calls.append(args)
        return self.return_value


def test_inspect_prints_font_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    font = tmp_path / "Demo.ttf"
    monkeypatch.setattr(inspect_module, "find", lambda source: iter([font]))
    monkeypatch.setattr(
        inspect_module,
        "reg_name",
        lambda path: "Demo Regular (TrueType)",
    )
    monkeypatch.setattr(inspect_module, "kind", lambda path: "TrueType")

    inspect_module.inspect(tmp_path)

    assert capsys.readouterr().out == (
        f"{font}\n  Registry name: Demo Regular (TrueType)\n  Kind: TrueType\n"
    )


def test_inspect_reports_when_no_fonts_are_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(inspect_module, "find", lambda source: iter([]))

    inspect_module.inspect(tmp_path)

    assert capsys.readouterr().out == f"No supported font files found in: {tmp_path}\n"


def test_get_windows_build_number_reads_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(env_module.winreg, "OpenKey", lambda *args: FakeRegistryKey())
    monkeypatch.setattr(
        env_module.winreg,
        "QueryValueEx",
        lambda key, name: ("22631", 1),
    )

    assert env_module.get_windows_build_number() == 22631


def test_is_admin_uses_shell32_and_falls_back_to_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        env_module.ctypes,
        "windll",
        SimpleNamespace(shell32=SimpleNamespace(IsUserAnAdmin=lambda: 1)),
    )

    assert env_module.is_admin() is True

    def raising_admin_check() -> bool:
        raise OSError("unavailable")

    monkeypatch.setattr(
        env_module.ctypes,
        "windll",
        SimpleNamespace(shell32=SimpleNamespace(IsUserAnAdmin=raising_admin_check)),
    )

    assert env_module.is_admin() is False


def test_add_and_remove_font_resource_call_gdi32(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    add = FakeWinFunction(2)
    remove = FakeWinFunction(1)
    fake_gdi32 = SimpleNamespace(AddFontResourceW=add, RemoveFontResourceW=remove)
    monkeypatch.setattr(
        active_module.ctypes, "WinDLL", lambda *args, **kwargs: fake_gdi32
    )
    font_path = tmp_path / "Demo.ttf"

    assert active_module.add_font_resource(font_path) == 2
    assert active_module.remove_font_resource(font_path) is True
    assert add.calls == [(str(font_path),)]
    assert remove.calls == [(str(font_path),)]


def test_broadcast_font_change_sends_wm_fontchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    send = FakeWinFunction(1)
    monkeypatch.setattr(
        active_module.ctypes,
        "WinDLL",
        lambda *args, **kwargs: SimpleNamespace(SendMessageTimeoutW=send),
    )

    active_module.broadcast_font_change()

    hwnd, message, wparam, lparam, flags, timeout, result = send.calls[0]
    assert hwnd == 0xFFFF
    assert message == 0x001D
    assert wparam == 0
    assert lparam == 0
    assert flags == 0x0002
    assert timeout == 1000
    assert result is not None


def test_broadcast_font_change_warns_when_windows_reports_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    send = FakeWinFunction(0)
    monkeypatch.setattr(
        active_module.ctypes,
        "WinDLL",
        lambda *args, **kwargs: SimpleNamespace(SendMessageTimeoutW=send),
    )
    monkeypatch.setattr(active_module.ctypes, "get_last_error", lambda: 5)
    monkeypatch.setattr(
        active_module.ctypes, "WinError", lambda error: f"winerr {error}"
    )

    active_module.broadcast_font_change()

    assert (
        "Warning: WM_FONTCHANGE broadcast failed: winerr 5" in capsys.readouterr().out
    )
