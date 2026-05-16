from __future__ import annotations

from typing import Annotated

import typer

from fonti.uninstall import (
    UninstallTarget,
    resolve_uninstall_target,
    uninstall_by_filters,
    uninstall_font_targets,
)
from fonti.win.env import is_admin


def uninstall_cmd(
    targets: Annotated[
        list[str] | None,
        typer.Argument(help="Registry font names or files to uninstall."),
    ] = None,
    is_global: Annotated[
        bool,
        typer.Option(
            "--global",
            "-g",
            help="Uninstall from global fonts. Requires admin privileges.",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Confirm operations that may remove multiple fonts (like regex).",
        ),
    ] = False,
    name_regex: Annotated[
        str | None,
        typer.Option(
            "--name-regex",
            "-e",
            help=(
                "Only uninstall fonts whose registry name matches this regex. "
                "Matching is case-insensitive."
            ),
        ),
    ] = None,
) -> None:
    """Uninstall fonts."""
    if is_global and not is_admin():
        raise SystemExit("Error: Global font uninstall requires admin privileges.")

    if not targets and not name_regex:
        raise SystemExit(
            "Error: rm requires at least one target or a --name-regex (-e)."
        )

    if name_regex:
        if not yes:
            raise SystemExit(
                "Error: Filtered uninstall can remove multiple fonts. "
                "Preview with matching `fonti ls` filters, then re-run with -y / --yes."
            )
        uninstall_by_filters(name_regex=name_regex, is_global=is_global)

    if targets:
        resolved_targets: list[UninstallTarget] = []
        for token in targets:
            found = list(resolve_uninstall_target(token, is_global=is_global))
            if not found:
                raise SystemExit(f"Error: No installed font matched '{token}'.")
            resolved_targets.extend(found)

        uninstall_font_targets(resolved_targets, is_global=is_global)
