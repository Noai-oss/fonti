from __future__ import annotations

import sys
from collections.abc import Sequence

import click
import typer

from fonti.cli import app


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the fonti CLI."""
    try:
        app(prog_name="fonti", args=argv, standalone_mode=False)
        return 0
    except typer.Exit as exc:
        return exc.exit_code
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        return exc.exit_code
    except (KeyboardInterrupt, typer.Abort):
        typer.echo("Interrupted.", err=True)
        return 130
    except SystemExit as exc:
        if exc.code is None:
            return 0
        if isinstance(exc.code, int):
            return exc.code

        typer.echo(str(exc.code), err=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
