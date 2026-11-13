from pathlib import Path
from typing import Annotated

import typer

from fonti.info import show_info
from fonti.install import install
from fonti.ls import list_installed_fonts
from fonti.uninstall import remove

app = typer.Typer(
    name="fonti",
    help="Install and manage Windows fonts. Start with: fonti install PATH",
    add_completion=False,
    no_args_is_help=True,
)
SystemScope = Annotated[
    bool,
    typer.Option("--system", help="Use system fonts instead of current-user fonts."),
]


@app.command("install")
def install_cmd(
    paths: Annotated[
        list[Path], typer.Argument(help="Font files or directories (recursive).")
    ],
    system: SystemScope = False,
    replace: Annotated[
        bool,
        typer.Option(
            "--replace", help="Allow replacing different contents at the same filename."
        ),
    ] = False,
) -> None:
    """Install one or more font files or directories."""
    install(paths, system=system, replace=replace)


@app.command("list")
def list_cmd(
    keyword: Annotated[
        str, typer.Argument(help="Literal text in the installed name or filename.")
    ] = "",
    system: SystemScope = False,
) -> None:
    """List installed names and filenames, optionally filtering by keyword."""
    list_installed_fonts(is_global=system, keyword=keyword)


@app.command("remove")
def remove_cmd(
    targets: Annotated[
        list[str],
        typer.Argument(help="Exact installed names or filenames from 'fonti list'."),
    ],
    system: SystemScope = False,
) -> None:
    """Remove one or more installed fonts."""
    remove(targets, system=system)


@app.command("info")
def info_cmd(
    path: Annotated[Path, typer.Argument(help="Font file or directory (recursive).")],
) -> None:
    """Inspect font names before installing."""
    show_info(path)
