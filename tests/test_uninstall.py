from __future__ import annotations

from pathlib import Path

import pytest

import fonti.uninstall as uninstall_module
from fonti.ls import InstalledFont


class FakeRegistryKey:
    def __enter__(self) -> "FakeRegistryKey":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def test_ensure_font_file_removable_allows_missing_files(tmp_path: Path) -> None:
    uninstall_module.ensure_font_file_removable(tmp_path / "missing.ttf", "Missing")


def test_ensure_font_file_removable_reports_locked_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    font_path = tmp_path / "Locked.ttf"
    font_path.write_text("locked")

    def locked_rename(self: Path, target: Path) -> Path:
        raise OSError("in use")

    monkeypatch.setattr(Path, "rename", locked_rename)

    with pytest.raises(SystemExit, match="font file is in use"):
        uninstall_module.ensure_font_file_removable(font_path, "Locked")


def test_uninstall_font_targets_removes_file_registry_and_broadcasts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    font_path = tmp_path / "Demo.ttf"
    font_path.write_text("font bytes")
    target = uninstall_module.UninstallTarget("Demo Regular (TrueType)", font_path)
    deleted_values: list[str] = []
    removed_resources: list[Path] = []
    broadcasts: list[bool] = []

    monkeypatch.setattr(uninstall_module, "get_registry_root", lambda is_global: "HKCU")
    monkeypatch.setattr(
        uninstall_module.winreg,
        "OpenKey",
        lambda *args: FakeRegistryKey(),
    )
    monkeypatch.setattr(
        uninstall_module.winreg,
        "DeleteValue",
        lambda key, name: deleted_values.append(name),
    )
    monkeypatch.setattr(
        uninstall_module,
        "remove_font_resource",
        lambda path: removed_resources.append(path) or True,
    )
    monkeypatch.setattr(
        uninstall_module,
        "broadcast_font_change",
        lambda: broadcasts.append(True),
    )

    uninstall_module.uninstall_font_targets([target], is_global=False)

    assert not font_path.exists()
    assert deleted_values == ["Demo Regular (TrueType)"]
    assert removed_resources == [font_path]
    assert broadcasts == [True]
    assert "Uninstalled: Demo Regular (TrueType)" in capsys.readouterr().out


def test_uninstall_font_targets_noops_for_empty_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        uninstall_module.winreg,
        "OpenKey",
        lambda *args: pytest.fail("registry should not be opened"),
    )

    uninstall_module.uninstall_font_targets([], is_global=False)


def test_resolve_uninstall_target_by_file_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_dir = tmp_path / "fonts"
    installed_path = install_dir / "Demo.ttf"

    monkeypatch.setattr(
        uninstall_module,
        "get_font_install_dir",
        lambda is_global: install_dir,
    )
    monkeypatch.setattr(
        uninstall_module,
        "iter_font_registry_values",
        lambda is_global: iter([("Demo Regular (TrueType)", str(installed_path), 1)]),
    )

    assert list(uninstall_module.resolve_uninstall_target("Demo.ttf")) == [
        uninstall_module.UninstallTarget("Demo Regular (TrueType)", installed_path)
    ]


def test_resolve_uninstall_target_by_registry_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    font_path = tmp_path / "Demo.ttf"

    monkeypatch.setattr(uninstall_module, "get_registry_root", lambda is_global: "HKCU")
    monkeypatch.setattr(
        uninstall_module.winreg,
        "OpenKey",
        lambda *args: FakeRegistryKey(),
    )
    monkeypatch.setattr(
        uninstall_module.winreg,
        "QueryValueEx",
        lambda key, token: ("Demo.ttf", 1),
    )
    monkeypatch.setattr(
        uninstall_module,
        "resolve_registry_font_path",
        lambda value, is_global: font_path,
    )

    assert list(
        uninstall_module.resolve_uninstall_target("Demo Regular (TrueType)")
    ) == [uninstall_module.UninstallTarget("Demo Regular (TrueType)", font_path)]


def test_resolve_uninstall_target_returns_empty_for_missing_registry_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(uninstall_module, "get_registry_root", lambda is_global: "HKCU")

    def missing_key(*args: object) -> FakeRegistryKey:
        raise FileNotFoundError

    monkeypatch.setattr(uninstall_module.winreg, "OpenKey", missing_key)

    assert list(uninstall_module.resolve_uninstall_target("Missing Regular")) == []


def test_uninstall_by_filters_validates_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(SystemExit, match="require --name-regex"):
        uninstall_module.uninstall_by_filters(None)

    monkeypatch.setattr(
        uninstall_module,
        "find_installed_fonts",
        lambda is_global=False, name_regex=None: iter([]),
    )

    with pytest.raises(SystemExit, match="No installed fonts matched filters"):
        uninstall_module.uninstall_by_filters("missing")


def test_uninstall_by_filters_delegates_matching_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    font = InstalledFont(
        "Demo Regular (TrueType)",
        "Demo.ttf",
        tmp_path / "Demo.ttf",
    )
    calls: list[tuple[list[uninstall_module.UninstallTarget], bool]] = []

    monkeypatch.setattr(
        uninstall_module,
        "find_installed_fonts",
        lambda is_global=False, name_regex=None: iter([font]),
    )
    monkeypatch.setattr(
        uninstall_module,
        "uninstall_font_targets",
        lambda targets, is_global: calls.append((list(targets), is_global)),
    )

    uninstall_module.uninstall_by_filters("demo", is_global=True)

    assert calls == [
        (
            [
                uninstall_module.UninstallTarget(
                    "Demo Regular (TrueType)",
                    tmp_path / "Demo.ttf",
                )
            ],
            True,
        )
    ]
