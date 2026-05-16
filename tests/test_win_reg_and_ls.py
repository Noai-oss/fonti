from __future__ import annotations

from pathlib import Path

import pytest

import fonti.ls as ls_module
import fonti.win.reg as reg_module


class FakeRegistryKey:
    def __enter__(self) -> "FakeRegistryKey":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def test_registry_roots_and_font_install_dirs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_app_data = tmp_path / "LocalAppData"
    windir = tmp_path / "Windows"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("WINDIR", str(windir))

    assert reg_module.get_registry_root(False) == reg_module.winreg.HKEY_CURRENT_USER
    assert reg_module.get_registry_root(True) == reg_module.winreg.HKEY_LOCAL_MACHINE
    assert reg_module.get_font_install_dir(False) == (
        local_app_data / "Microsoft" / "Windows" / "Fonts"
    )
    assert reg_module.get_font_install_dir(True) == windir / "Fonts"


def test_registry_value_data_and_path_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user_font = tmp_path / "UserFonts" / "Demo.ttf"
    global_dir = tmp_path / "Windows" / "Fonts"
    monkeypatch.setenv("WINDIR", str(tmp_path / "Windows"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))

    assert reg_module.get_registry_value_data(user_font, is_global=False) == str(
        user_font
    )
    assert reg_module.get_registry_value_data(global_dir / "Demo.ttf", True) == (
        "Demo.ttf"
    )
    assert reg_module.resolve_registry_font_path(str(user_font), False) == user_font
    assert reg_module.resolve_registry_font_path("Demo.ttf", True) == (
        global_dir / "Demo.ttf"
    )


def test_iter_font_registry_values_enumerates_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = [
        ("Demo Regular (TrueType)", "Demo.ttf", reg_module.winreg.REG_SZ),
        ("Mono Regular (TrueType)", "Mono.ttf", reg_module.winreg.REG_SZ),
    ]

    monkeypatch.setattr(
        reg_module.winreg,
        "OpenKey",
        lambda *args: FakeRegistryKey(),
    )
    monkeypatch.setattr(
        reg_module.winreg,
        "QueryInfoKey",
        lambda key: (0, len(values), 0),
    )
    monkeypatch.setattr(
        reg_module.winreg,
        "EnumValue",
        lambda key, index: values[index],
    )

    assert list(reg_module.iter_font_registry_values(False)) == values


def test_iter_font_registry_values_treats_missing_key_as_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_key(*args: object) -> FakeRegistryKey:
        raise FileNotFoundError

    monkeypatch.setattr(reg_module.winreg, "OpenKey", missing_key)

    assert list(reg_module.iter_font_registry_values(False)) == []


def test_find_installed_fonts_filters_names(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [
        ("Demo Regular (TrueType)", r"C:\Fonts\Demo.ttf", reg_module.winreg.REG_SZ),
        ("Mono Regular (TrueType)", r"C:\Fonts\Mono.ttf", reg_module.winreg.REG_SZ),
    ]
    monkeypatch.setattr(
        ls_module,
        "iter_font_registry_values",
        lambda is_global: iter(values),
    )
    monkeypatch.setattr(
        ls_module,
        "resolve_registry_font_path",
        lambda value, is_global: Path(value),
    )

    assert list(ls_module.find_installed_fonts(name_regex="mono")) == [
        ls_module.InstalledFont(
            "Mono Regular (TrueType)",
            r"C:\Fonts\Mono.ttf",
            Path(r"C:\Fonts\Mono.ttf"),
        )
    ]


def test_list_installed_fonts_prints_pipeline_friendly_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    font = ls_module.InstalledFont(
        "Demo Regular (TrueType)",
        r"C:\Fonts\Demo.ttf",
        Path(r"C:\Fonts\Demo.ttf"),
    )
    monkeypatch.setattr(
        ls_module,
        "find_installed_fonts",
        lambda is_global=False, name_regex=None: iter([font]),
    )

    ls_module.list_installed_fonts(name_regex="demo")

    assert capsys.readouterr().out == (
        "Demo Regular (TrueType)\tC:\\Fonts\\Demo.ttf\tC:\\Fonts\\Demo.ttf\n"
    )
