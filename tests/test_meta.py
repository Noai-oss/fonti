from __future__ import annotations

from pathlib import Path
from typing import cast

from fontTools.ttLib import TTFont
import pytest

import fonti.meta as meta_module


class FakeNameTable:
    def __init__(
        self,
        *,
        full: str | None = None,
        family: str | None = None,
        subfamily: str | None = None,
    ) -> None:
        self.full = full
        self.family = family
        self.subfamily = subfamily

    def getBestFullName(self) -> str | None:
        return self.full

    def getBestFamilyName(self) -> str | None:
        return self.family

    def getBestSubFamilyName(self) -> str | None:
        return self.subfamily


class FakeFont:
    def __init__(self, name_table: FakeNameTable) -> None:
        self.name_table = name_table

    def __getitem__(self, key: str) -> FakeNameTable:
        assert key == "name"
        return self.name_table


class FontContext:
    def __init__(self, font: FakeFont) -> None:
        self.font = font

    def __enter__(self) -> FakeFont:
        return self.font

    def __exit__(self, *exc_info: object) -> None:
        return None


class CollectionContext:
    def __init__(self, fonts: list[FakeFont]) -> None:
        self.fonts = fonts

    def __enter__(self) -> "CollectionContext":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def as_ttfont(font: FakeFont) -> TTFont:
    return cast(TTFont, font)


def test_kind_maps_supported_fonts_to_truetype() -> None:
    for suffix in [".ttf", ".TTF", ".otf", ".ttc", ".otc"]:
        assert meta_module.kind(Path(f"Demo{suffix}")) == "TrueType"


def test_kind_rejects_unsupported_font_types() -> None:
    with pytest.raises(ValueError, match="unsupported font type"):
        meta_module.kind(Path("Demo.woff"))


def test_normalize_font_name_collapses_whitespace() -> None:
    assert meta_module.normalize_font_name("  Demo   Font\nRegular  ") == (
        "Demo Font Regular"
    )
    assert meta_module.normalize_font_name("   ") is None
    assert meta_module.normalize_font_name(None) is None


def test_get_font_display_name_uses_best_available_name() -> None:
    assert (
        meta_module.get_font_display_name(
            as_ttfont(FakeFont(FakeNameTable(full=" Demo  Regular "))),
            fallback="Fallback",
        )
        == "Demo Regular"
    )
    assert (
        meta_module.get_font_display_name(
            as_ttfont(FakeFont(FakeNameTable(family="Demo", subfamily="Bold"))),
            fallback="Fallback",
        )
        == "Demo Bold"
    )
    assert (
        meta_module.get_font_display_name(
            as_ttfont(FakeFont(FakeNameTable(family="Demo"))),
            fallback="Fallback",
        )
        == "Demo"
    )
    assert (
        meta_module.get_font_display_name(
            as_ttfont(FakeFont(FakeNameTable())), fallback="Fallback"
        )
        == "Fallback"
    )


def test_reg_name_reads_single_face_font(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake_ttfont(path: str, fontNumber: int = 0) -> FontContext:
        calls.append((path, fontNumber))
        return FontContext(FakeFont(FakeNameTable(full="Demo Regular")))

    monkeypatch.setattr(meta_module, "TTFont", fake_ttfont)

    font_path = Path("Demo.ttf")

    assert meta_module.reg_name(font_path) == "Demo Regular (TrueType)"
    assert calls == [(str(font_path.resolve()), 0)]


def test_reg_name_reads_collection_faces_and_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fonts = [
        FakeFont(FakeNameTable(full="Alpha")),
        FakeFont(FakeNameTable(full=" alpha ")),
        FakeFont(FakeNameTable(family="Beta", subfamily="Regular")),
    ]
    calls: list[str] = []

    def fake_collection(path: str) -> CollectionContext:
        calls.append(path)
        return CollectionContext(fonts)

    monkeypatch.setattr(meta_module, "TTCollection", fake_collection)

    font_path = Path("Collection.ttc")

    assert meta_module.reg_name(font_path) == "Alpha & Beta Regular (TrueType)"
    assert calls == [str(font_path.resolve())]
