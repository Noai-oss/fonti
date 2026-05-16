from __future__ import annotations

from pathlib import Path

import pytest

import fonti.install as install_module


class FakeRegistryKey:
    def __enter__(self) -> "FakeRegistryKey":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def test_install_copies_registers_activates_and_broadcasts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_font = source_dir / "Demo.ttf"
    source_font.write_text("font bytes")
    target_dir = tmp_path / "installed"
    target_path = target_dir / "Demo.ttf"

    registry_values: list[tuple[str, str]] = []
    add_calls: list[Path] = []
    broadcast_calls: list[bool] = []

    monkeypatch.setattr(
        install_module,
        "get_windows_build_number",
        lambda: install_module.WIN10_1809_BUILD,
    )
    monkeypatch.setattr(
        install_module, "get_font_install_dir", lambda is_global: target_dir
    )
    monkeypatch.setattr(install_module, "get_registry_root", lambda is_global: "HKCU")
    monkeypatch.setattr(
        install_module,
        "reg_name",
        lambda path: "Demo Regular (TrueType)",
    )
    monkeypatch.setattr(
        install_module.winreg,
        "CreateKeyEx",
        lambda *args: FakeRegistryKey(),
    )
    monkeypatch.setattr(
        install_module.winreg,
        "SetValueEx",
        lambda key, name, reserved, value_type, value: registry_values.append(
            (name, value)
        ),
    )
    monkeypatch.setattr(
        install_module,
        "add_font_resource",
        lambda path: add_calls.append(path) or 1,
    )
    monkeypatch.setattr(
        install_module,
        "broadcast_font_change",
        lambda: broadcast_calls.append(True),
    )

    install_module.install(source_dir)

    assert target_path.read_text() == "font bytes"
    assert registry_values == [("Demo Regular (TrueType)", str(target_path))]
    assert add_calls == [target_path]
    assert broadcast_calls == [True]
    assert "Installed persistently: Demo Regular (TrueType)" in capsys.readouterr().out


def test_install_rejects_unsupported_scopes_before_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        install_module,
        "get_windows_build_number",
        lambda: install_module.WIN10_1809_BUILD - 1,
    )

    with pytest.raises(SystemExit, match="too old for user-level fonts"):
        install_module.install(tmp_path, is_global=False)

    monkeypatch.setattr(
        install_module,
        "get_windows_build_number",
        lambda: install_module.WIN10_1809_BUILD,
    )
    monkeypatch.setattr(install_module, "is_admin", lambda: False)

    with pytest.raises(SystemExit, match="requires admin privileges"):
        install_module.install(tmp_path, is_global=True)


def test_install_skips_existing_target_without_force(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_font = tmp_path / "source" / "Demo.ttf"
    source_font.parent.mkdir()
    source_font.write_text("new bytes")
    target_dir = tmp_path / "installed"
    target_dir.mkdir()
    target_path = target_dir / "Demo.ttf"
    target_path.write_text("existing bytes")

    broadcasts: list[bool] = []

    monkeypatch.setattr(
        install_module,
        "get_windows_build_number",
        lambda: install_module.WIN10_1809_BUILD,
    )
    monkeypatch.setattr(
        install_module, "get_font_install_dir", lambda is_global: target_dir
    )
    monkeypatch.setattr(install_module, "get_registry_root", lambda is_global: "HKCU")
    monkeypatch.setattr(
        install_module,
        "reg_name",
        lambda path: "Demo Regular (TrueType)",
    )
    monkeypatch.setattr(
        install_module.winreg,
        "CreateKeyEx",
        lambda *args: pytest.fail("registry should not be opened for skipped fonts"),
    )
    monkeypatch.setattr(
        install_module,
        "add_font_resource",
        lambda path: pytest.fail("skipped fonts should not be activated"),
    )
    monkeypatch.setattr(
        install_module,
        "broadcast_font_change",
        lambda: broadcasts.append(True),
    )

    install_module.install(source_font)

    assert target_path.read_text() == "existing bytes"
    assert broadcasts == []
    assert f"Skip existing file: {target_path}" in capsys.readouterr().out


def test_install_reports_immediate_activation_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_font = tmp_path / "Demo.ttf"
    source_font.write_text("font bytes")
    target_dir = tmp_path / "installed"

    monkeypatch.setattr(
        install_module,
        "get_windows_build_number",
        lambda: install_module.WIN10_1809_BUILD,
    )
    monkeypatch.setattr(
        install_module, "get_font_install_dir", lambda is_global: target_dir
    )
    monkeypatch.setattr(install_module, "get_registry_root", lambda is_global: "HKCU")
    monkeypatch.setattr(
        install_module,
        "reg_name",
        lambda path: "Demo Regular (TrueType)",
    )
    monkeypatch.setattr(
        install_module.winreg,
        "CreateKeyEx",
        lambda *args: FakeRegistryKey(),
    )
    monkeypatch.setattr(install_module.winreg, "SetValueEx", lambda *args: None)
    monkeypatch.setattr(install_module, "add_font_resource", lambda path: 0)
    monkeypatch.setattr(install_module, "broadcast_font_change", lambda: None)

    install_module.install(source_font)

    assert "Immediate activation: failed; reboot may be required." in (
        capsys.readouterr().out
    )


def test_install_reports_when_no_fonts_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "installed"
    source_dir.mkdir()
    (source_dir / "Demo.woff").write_text("unsupported")
    broadcasts: list[bool] = []

    monkeypatch.setattr(
        install_module,
        "get_windows_build_number",
        lambda: install_module.WIN10_1809_BUILD,
    )
    monkeypatch.setattr(
        install_module, "get_font_install_dir", lambda is_global: target_dir
    )
    monkeypatch.setattr(install_module, "get_registry_root", lambda is_global: "HKCU")
    monkeypatch.setattr(
        install_module.winreg,
        "CreateKeyEx",
        lambda *args: pytest.fail("registry should not be opened without matches"),
    )
    monkeypatch.setattr(
        install_module,
        "broadcast_font_change",
        lambda: broadcasts.append(True),
    )

    install_module.install(source_dir)

    assert not target_dir.exists()
    assert broadcasts == []
    assert f"No valid/matching font files found in: {source_dir}" in (
        capsys.readouterr().out
    )
