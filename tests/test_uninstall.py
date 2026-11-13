from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from fonti import uninstall
from fonti.__main__ import main
from fonti.ls import InstalledFont


@pytest.fixture
def windows(monkeypatch, tmp_path):
    directory = tmp_path / "fonts"
    directory.mkdir()
    path = directory / "Demo.ttf"
    path.write_bytes(b"font")
    values = {"Demo Regular (TrueType)": path}
    removed, activated, broadcasts = [], [], []
    monkeypatch.setattr(
        uninstall,
        "find_installed_fonts",
        lambda system: [InstalledFont(name, path) for name, path in values.items()],
    )
    monkeypatch.setattr(uninstall, "get_font_install_dir", lambda system: directory)
    monkeypatch.setattr(uninstall.winreg, "OpenKey", lambda *args: nullcontext())
    monkeypatch.setattr(
        uninstall.winreg,
        "QueryValueEx",
        lambda key, name: (str(values[name]), uninstall.winreg.REG_SZ),
    )
    monkeypatch.setattr(
        uninstall.winreg,
        "SetValueEx",
        lambda key, name, reserved, typ, value: values.update(
            {name: type(path)(value)}
        ),
    )
    monkeypatch.setattr(
        uninstall.winreg, "DeleteValue", lambda key, name: values.pop(name)
    )
    monkeypatch.setattr(
        uninstall, "remove_font_resource", lambda path: removed.append(path) or True
    )
    monkeypatch.setattr(
        uninstall, "add_font_resource", lambda path: activated.append(path) or 1
    )
    monkeypatch.setattr(
        uninstall, "broadcast_font_change", lambda: broadcasts.append(True)
    )
    return SimpleNamespace(
        path=path,
        values=values,
        removed=removed,
        activated=activated,
        broadcasts=broadcasts,
    )


@pytest.mark.parametrize("bad", ["missing.ttf", "Demo", "Demo.*"])
def test_missing_or_partial_target_does_not_remove_anything(windows, bad, capsys):
    assert main(["remove", "Demo.ttf", bad]) == 1
    assert bad in capsys.readouterr().err
    assert windows.values and windows.path.exists()
    assert not windows.removed and not windows.broadcasts


def test_overlapping_targets_removed_once(windows):
    assert main(["remove", "DEMO.ttf", "demo regular (truetype)", "Demo.ttf"]) == 0
    assert not windows.path.exists() and not windows.values
    assert windows.removed == [windows.path]
    assert windows.broadcasts == [True]


def test_ambiguous_filename_and_shared_file_ownership(windows, capsys):
    windows.values["Another Name"] = windows.path
    assert main(["remove", "Another Name", "Demo.ttf"]) == 1
    assert "Ambiguous" in capsys.readouterr().err
    assert len(windows.values) == 2 and windows.path.exists()
    assert main(["remove", "Another Name"]) == 0
    assert windows.path.exists() and not windows.removed
    assert main(["remove", "Demo.ttf"]) == 0
    assert not windows.path.exists() and not windows.values
    assert windows.removed == [windows.path]


def test_external_font_only_unregisters(windows, tmp_path):
    source = tmp_path / "External.otf"
    source.write_bytes(b"original")
    windows.values["External"] = source
    assert main(["remove", "external.OTF"]) == 0
    assert "External" not in windows.values
    assert source.read_bytes() == b"original"
    assert windows.removed == [source]


def test_missing_file_can_still_be_unregistered(windows):
    windows.path.unlink()
    assert main(["remove", "Demo.ttf"]) == 0
    assert not windows.values and not windows.removed


def test_registry_failure_preserves_file_and_immediate_activation(
    windows, monkeypatch, capsys
):
    def denied(key, name):
        raise PermissionError("registration changed")

    monkeypatch.setattr(uninstall.winreg, "DeleteValue", denied)
    assert main(["remove", "Demo.ttf"]) == 1
    assert "registration changed" in capsys.readouterr().err
    assert windows.values and windows.path.exists()
    assert not windows.removed


def test_locked_file_reports_error_and_restores_activation(
    windows, monkeypatch, capsys
):
    def locked(path):
        raise PermissionError("in use")

    monkeypatch.setattr(type(windows.path), "unlink", locked)
    assert main(["remove", "Demo.ttf"]) == 1
    assert str(windows.path) in capsys.readouterr().err
    assert windows.values and windows.path.exists()
    assert windows.activated == [windows.path]


def test_deactivation_failure_with_successful_removal_is_a_warning(
    windows, monkeypatch, capsys
):
    monkeypatch.setattr(uninstall, "remove_font_resource", lambda path: False)
    assert main(["remove", "Demo.ttf"]) == 0
    assert "Immediate deactivation failed" in capsys.readouterr().err
    assert not windows.values


def test_system_remove_requires_admin(windows, monkeypatch, capsys):
    monkeypatch.setattr(uninstall, "is_admin", lambda: False)
    assert main(["remove", "--system", "Demo.ttf"]) == 1
    assert "administrator" in capsys.readouterr().err
    assert windows.path.exists() and windows.values
