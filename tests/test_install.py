from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

import fonti.install as installer
from fonti.__main__ import main
from fonti.ls import InstalledFont


@pytest.fixture
def windows(monkeypatch, tmp_path):
    target = tmp_path / "installed"
    values = {}
    activated, deactivated, broadcasts = [], [], []
    source = tmp_path / "Demo.ttf"
    source.write_bytes(b"font bytes")
    monkeypatch.setattr(
        installer, "get_windows_build_number", lambda: installer.WIN10_1809_BUILD
    )
    monkeypatch.setattr(installer, "get_font_install_dir", lambda system: target)
    monkeypatch.setattr(installer, "reg_name", lambda file: file.stem)
    monkeypatch.setattr(
        installer,
        "find_installed_fonts",
        lambda system: (
            InstalledFont(
                name,
                value,
                Path(value) if Path(value).is_absolute() else target / value,
            )
            for name, value in values.items()
        ),
    )
    monkeypatch.setattr(installer.winreg, "CreateKeyEx", lambda *args: nullcontext())
    monkeypatch.setattr(
        installer.winreg,
        "SetValueEx",
        lambda key, name, reserved, typ, value: values.update({name: value}),
    )
    monkeypatch.setattr(
        installer, "add_font_resource", lambda path: activated.append(path) or 1
    )
    monkeypatch.setattr(
        installer, "remove_font_resource", lambda path: deactivated.append(path) or True
    )
    monkeypatch.setattr(
        installer, "broadcast_font_change", lambda: broadcasts.append(True)
    )
    return SimpleNamespace(
        source=source,
        target=target / source.name,
        values=values,
        activated=activated,
        deactivated=deactivated,
        broadcasts=broadcasts,
    )


def test_install_directory_and_overlapping_paths(windows, capsys):
    w = windows
    sub = w.source.parent / "nested"
    sub.mkdir()
    (sub / "Second.otf").write_bytes(b"another font")
    assert main(["install", str(w.source.parent), str(w.source)]) == 0
    assert w.target.read_bytes() == w.source.read_bytes()
    assert w.values == {
        "Demo": str(w.target),
        "Second": str(w.target.with_name("Second.otf")),
    }
    assert set(w.activated) == {w.target, w.target.with_name("Second.otf")}
    assert w.broadcasts == [True]
    assert "Already installed: Demo" in capsys.readouterr().out


def test_retry_after_registry_write_failure(windows, monkeypatch, capsys):
    w = windows

    def fail(*args):
        raise PermissionError("test registry write denied")

    with monkeypatch.context() as first:
        first.setattr(installer.winreg, "SetValueEx", fail)
        assert main(["install", str(w.source)]) == 1
    assert str(w.source) in capsys.readouterr().err
    assert w.target.read_bytes() == w.source.read_bytes()
    assert not w.values
    assert main(["install", str(w.source)]) == 0
    assert w.values == {"Demo": str(w.target)}
    assert main(["install", str(w.target)]) == 0
    assert w.activated == [w.target]
    assert w.broadcasts == [True]


def test_conflict_requires_explicit_replace_even_for_same_length(windows, capsys):
    w = windows
    assert main(["install", str(w.source)]) == 0
    old = w.target.read_bytes()
    w.source.write_bytes(b"x" * len(old))
    assert main(["install", str(w.source)]) == 1
    assert "--replace" in capsys.readouterr().err
    assert w.target.read_bytes() == old
    assert main(["install", str(w.source), "--replace"]) == 0
    assert w.target.read_bytes() == w.source.read_bytes()
    assert w.deactivated == [w.target]


def test_failed_replacement_preserves_previous_file(windows, monkeypatch, capsys):
    w = windows
    assert main(["install", str(w.source)]) == 0
    original = w.target.read_bytes()
    w.source.write_bytes(b"version two")

    def fail(staged, destination):
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "replace", fail)
    assert main(["install", str(w.source), "--replace"]) == 1
    assert "locked" in capsys.readouterr().err
    assert w.target.read_bytes() == original
    assert list(w.target.parent.iterdir()) == [w.target]
    assert w.activated == [w.target, w.target]


def test_registry_name_pointing_elsewhere_is_a_conflict(windows, capsys):
    w = windows
    other = w.target.with_name("other.ttf")
    w.values["Demo"] = str(other)
    assert main(["install", str(w.source), "--replace"]) == 1
    assert str(other) in capsys.readouterr().err
    assert not w.target.exists()
    assert w.values == {"Demo": str(other)}


def test_batch_reports_empty_input_and_broadcasts_completed_fonts(
    windows, tmp_path, capsys
):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["install", str(windows.source), str(empty)]) == 1
    assert str(empty) in capsys.readouterr().err
    assert windows.broadcasts == [True]


def test_immediate_activation_failure_is_a_warning(windows, monkeypatch, capsys):
    monkeypatch.setattr(installer, "add_font_resource", lambda path: 0)
    assert main(["install", str(windows.source)]) == 0
    assert windows.values
    assert "Immediate activation failed" in capsys.readouterr().err


def test_system_install_requires_admin_and_registers_filename(
    windows, monkeypatch, capsys
):
    monkeypatch.setattr(installer, "is_admin", lambda: False)
    assert main(["install", "--system", str(windows.source)]) == 1
    assert "administrator" in capsys.readouterr().err
    assert not windows.target.exists()
    monkeypatch.setattr(installer, "is_admin", lambda: True)
    assert main(["install", "--system", str(windows.source)]) == 0
    assert windows.values == {"Demo": windows.target.name}


def test_user_install_requires_supported_windows(windows, monkeypatch):
    monkeypatch.setattr(installer, "get_windows_build_number", lambda: 10000)
    assert main(["install", str(windows.source)]) == 1
    assert not windows.target.exists()


@pytest.mark.parametrize("command", ["install", "info"])
def test_corrupt_input_reports_filename_and_fails(tmp_path, capsys, command):
    source = tmp_path / "broken.ttf"
    source.write_bytes(b"bad font")
    assert main([command, str(source)]) == 1
    assert str(source) in capsys.readouterr().err
