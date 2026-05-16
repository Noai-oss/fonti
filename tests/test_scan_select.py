from __future__ import annotations

from pathlib import Path

import pytest

import fonti.scan as scan_module
import fonti.select as select_module


def test_find_yields_supported_file_sources(tmp_path: Path) -> None:
    font = tmp_path / "Demo.TTF"
    font.write_text("not a real font")
    ignored = tmp_path / "notes.txt"
    ignored.write_text("ignore me")

    assert list(scan_module.find(font)) == [font.resolve()]
    assert list(scan_module.find(ignored)) == []


def test_find_recurses_directories_in_stable_order(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    first = tmp_path / "A.ttf"
    second = nested / "B.otf"
    third = nested / "C.TTC"
    ignored = nested / "D.woff"

    for path in [second, ignored, third, first]:
        path.write_text("x")

    assert list(scan_module.find(tmp_path)) == [
        first.resolve(),
        second.resolve(),
        third.resolve(),
    ]


def test_find_rejects_missing_sources(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="source does not exist"):
        list(scan_module.find(tmp_path / "missing"))


def test_select_filters_by_format_filename_and_registry_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    alpha = tmp_path / "Alpha.ttf"
    beta = tmp_path / "Beta.otf"
    code = tmp_path / "Code.ttc"

    registry_names = {
        alpha: "Alpha Regular (TrueType)",
        beta: "Registry Mono (TrueType)",
        code: "Code Collection (TrueType)",
    }
    monkeypatch.setattr(select_module, "reg_name", lambda path: registry_names[path])

    assert list(
        select_module.select(
            [alpha, beta, code],
            name_regex="registry mono",
            formats=[".OTF"],
        )
    ) == [beta]

    assert list(select_module.select([alpha, beta, code], formats=["ttf"])) == [alpha]
    assert list(select_module.select([alpha, beta, code], name_regex="code")) == [code]


def test_select_reports_invalid_regex() -> None:
    with pytest.raises(SystemExit, match="Invalid --name-regex"):
        list(select_module.select([], name_regex="["))


def test_normalize_font_formats() -> None:
    assert select_module.normalize_font_formats(["TTF", ".otf"]) == {"ttf", "otf"}
    assert select_module.normalize_font_formats(None) == set()
