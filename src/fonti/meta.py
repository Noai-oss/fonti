from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont


def kind(path: Path) -> str:
    """Determine the Windows registry font kind from a font file extension."""
    match path.suffix.lower():
        case ".ttf" | ".ttc" | ".otf" | ".otc":
            return "TrueType"
        case _:
            raise ValueError(f"unsupported font type: {path}")


def normalize_font_name(value: str | None) -> str | None:
    """Normalize whitespace in a font name string."""
    if not value:
        return None

    value = " ".join(value.split())
    return value or None


def get_font_display_name(font: TTFont, fallback: str) -> str:
    """Return the best display name for a single face in a font file."""
    name_table = font["name"]

    if full_name := normalize_font_name(name_table.getBestFullName()):
        return full_name

    if family := normalize_font_name(name_table.getBestFamilyName()):
        if subfamily := normalize_font_name(name_table.getBestSubFamilyName()):
            return f"{family} {subfamily}"
        return family

    return fallback


def reg_name(font_path: Path) -> str:
    """
    Generate the Windows registry value name for a font file.

    Font collections (.ttc, .otc) may contain multiple faces, so their registry
    name joins each unique face name before adding the Windows font kind suffix.
    """
    font_path = font_path.resolve()
    k = kind(font_path)
    ext = font_path.suffix.lower()

    if ext in {".ttc", ".otc"}:
        with TTCollection(str(font_path)) as collection:
            names: list[str] = []
            seen: set[str] = set()

            for index, font in enumerate(collection.fonts):
                display_name = get_font_display_name(
                    font,
                    fallback=f"{font_path.stem}#{index}",
                )

                key = display_name.casefold()
                if key not in seen:
                    names.append(display_name)
                    seen.add(key)

            if names:
                return f"{' & '.join(names)} ({k})"

            return f"{font_path.stem} ({k})"

    with TTFont(str(font_path), fontNumber=0) as font:
        display_name = get_font_display_name(font, fallback=font_path.stem)
        return f"{display_name} ({k})"
