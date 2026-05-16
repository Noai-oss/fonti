from __future__ import annotations

from typing import Annotated

import typer

from fonti.ls import list_installed_fonts


def list_cmd(
    name_regex: Annotated[
        str | None,
        typer.Argument(
            help=(
                "Optional regex to filter fonts by registry name. "
                "Matching is case-insensitive."
            ),
        ),
    ] = None,
    is_global: Annotated[
        bool,
        typer.Option(
            "--global",
            "-g",
            help="List global fonts from HKLM instead of user fonts from HKCU.",
        ),
    ] = False,
) -> None:
    """List installed fonts."""
    list_installed_fonts(is_global=is_global, name_regex=name_regex)
