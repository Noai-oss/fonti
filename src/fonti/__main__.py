from __future__ import annotations

import sys
from collections.abc import Sequence

import typer

from fonti.cli import app


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the fonti CLI."""
    try:
        app(prog_name="fonti", args=argv, standalone_mode=True)
        return 0
    except typer.Exit as exc:
        return exc.exit_code
    except (OSError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        return 1
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
