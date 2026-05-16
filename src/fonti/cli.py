from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import click
import typer

from fonti.info import show_info
from fonti.install import install
from fonti.ls import list_installed_fonts
from fonti.uninstall import (
    UninstallTarget,
    resolve_uninstall_target,
    uninstall_by_filters,
    uninstall_font_targets,
)
from fonti.win.env import is_admin


FONT_FORMATS = ("ttf", "otf", "ttc", "otc")


def parse_opts(values: Sequence[str] | None) -> list[str] | None:
    """Parse comma-separated and repeated --format option values."""
    if not values:
        return None

    formats: list[str] = []
    invalid: list[str] = []

    for value in values:
        for item in value.split(","):
            font_format = item.strip().lower().removeprefix(".")

            if not font_format:
                continue

            if font_format not in FONT_FORMATS:
                invalid.append(font_format)
                continue

            if font_format not in formats:
                formats.append(font_format)

    if invalid:
        allowed = ", ".join(FONT_FORMATS)
        raise click.BadParameter(
            f"unsupported font format: {', '.join(invalid)} (choose from: {allowed})"
        )

    if not formats:
        raise click.BadParameter("expected at least one font format")

    return formats


app = typer.Typer(
    name="fonti",
    help="fonti: a command-line font installer for Windows",
    add_completion=False,
    no_args_is_help=True,
)


@app.command("info")
def info_cmd(
    source: Annotated[Path, typer.Argument(help="Font file or directory")],
) -> None:
    """Show font registry names."""
    show_info(source)


@app.command("install")
def install_cmd(
    source: Annotated[Path, typer.Argument(help="Font file or directory")],
    is_global: Annotated[
        bool,
        typer.Option(
            "--global",
            "-g",
            help="Install for all users. Requires admin privileges.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing font files."),
    ] = False,
    name_regex: Annotated[
        str | None,
        typer.Option(
            "--name-regex",
            "-e",
            help=(
                "Only install fonts whose file name, including extension, "
                "or registry name matches this regex. Matching is case-insensitive."
            ),
        ),
    ] = None,
    formats: Annotated[
        list[str] | None,
        typer.Option(
            "--format",
            callback=parse_opts,
            metavar="FORMAT[,FORMAT...]",
            help="Only install fonts with these formats. Use commas or repeat the option.",
        ),
    ] = None,
) -> None:
    """Install fonts."""
    install(
        source,
        is_global=is_global,
        force=force,
        name_regex=name_regex,
        formats=formats,
    )


@app.command("ls")
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


@app.command("rm")
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
