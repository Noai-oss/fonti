from __future__ import annotations

from pathlib import Path

import pytest

import fonti.scan as scan_module


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
