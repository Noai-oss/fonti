from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from fonti.meta import reg_name


def normalize_font_formats(formats: list[str] | None = None) -> set[str]:
    """Normalize parsed font formats for filtering."""
    if formats:
        return {font_format.casefold().removeprefix(".") for font_format in formats}

    return set()


def compile_name_regex(name_regex: str) -> re.Pattern[str]:
    """Compile a case-insensitive name regex with a CLI-friendly error."""
    try:
        return re.compile(name_regex, re.IGNORECASE)
    except re.error as exc:
        raise SystemExit(f"Error: Invalid --name-regex: {exc}") from exc


def select(
    font_files: Iterable[Path],
    name_regex: str | None = None,
    formats: list[str] | None = None,
) -> Iterator[Path]:
    """Select font files by extension and file/registry name."""
    allowed_formats = normalize_font_formats(formats)
    pattern = compile_name_regex(name_regex) if name_regex else None

    for font_file in font_files:
        if (
            allowed_formats
            and font_file.suffix.casefold().removeprefix(".") not in allowed_formats
        ):
            continue

        if pattern:
            if not pattern.search(font_file.name) and not pattern.search(
                reg_name(font_file)
            ):
                continue

        yield font_file
