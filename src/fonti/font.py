from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont

SUPPORTED_EXTS = {".ttf", ".otf", ".ttc", ".otc"}


def get_font_kind(path: Path) -> str:
    """Determine the font kind (TrueType or OpenType) based on file extension."""
    match path.suffix.lower():
        case ".ttf" | ".ttc" | ".otf" | ".otc":
            return "TrueType"
        # case ".otf" | ".otc":
        #     return "OpenType"
        case _:
            raise ValueError(f"unsupported font type: {path}")


def normalize_font_name_from_ttfont(value: str | None) -> str | None:
    """Normalize whitespace in a font name string."""
    if not value:
        return None
    value = " ".join(value.split())
    return value or None


def get_single_font_display_name(font: TTFont, fallback: str) -> str:
    """
    Get the display name of a single font, preferring Full Name,
    fallback to Family + SubFamily, or the provided fallback string.
    """
    name_table = font["name"]

    if full_name := normalize_font_name_from_ttfont(name_table.getBestFullName()):
        return full_name

    if family := normalize_font_name_from_ttfont(name_table.getBestFamilyName()):
        if subfamily := normalize_font_name_from_ttfont(
            name_table.getBestSubFamilyName()
        ):
            return f"{family} {subfamily}"
        return family

    return fallback


def get_font_registry_name(font_path: Path) -> str:
    """
    Generate the Windows registry value name for a given font file.
    Handles both single fonts and font collections (.ttc, .otc).
    """
    font_path = font_path.resolve()
    kind = get_font_kind(font_path)
    ext = font_path.suffix.lower()

    if ext in {".ttc", ".otc"}:
        with TTCollection(str(font_path)) as collection:
            names: list[str] = []
            seen: set[str] = set()

            for index, font in enumerate(collection.fonts):
                display_name = get_single_font_display_name(
                    font,
                    fallback=f"{font_path.stem}#{index}",
                )

                key = display_name.casefold()
                if key not in seen:
                    names.append(display_name)
                    seen.add(key)

            if names:
                return f"{' & '.join(names)} ({kind})"

            return f"{font_path.stem} ({kind})"

    with TTFont(str(font_path), fontNumber=0) as font:
        display_name = get_single_font_display_name(font, fallback=font_path.stem)
        return f"{display_name} ({kind})"


def get_font_files(source: Path) -> list[Path]:
    """
    Find all supported font files from a given source (file or directory).
    Recursively searches directories.
    """
    source = source.resolve()

    if source.is_file():
        if source.suffix.lower() in SUPPORTED_EXTS:
            return [source]

        return []

    if not source.exists():
        raise FileNotFoundError(f"source does not exist: {source}")

    if not source.is_dir():
        raise ValueError(f"source is not a file or directory: {source}")

    return sorted(
        p
        for p in source.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    )
