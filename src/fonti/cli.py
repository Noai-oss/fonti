from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.platform != "win32":
    raise SystemExit("Error: This tool is only supported on Windows.")

from fonti.windows import is_admin
from fonti.operations import (
    inspect_fonts,
    install_fonts,
    list_installed_fonts,
    uninstall_by_file,
    uninstall_by_registry_name,
)


def main() -> None:
    """CLI entry point. Parses arguments and routes to operations."""
    parser = argparse.ArgumentParser(
        prog="fonti",
        description="A command-line font installer for Windows.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="Inspect font registry names"
    )
    inspect_parser.add_argument("source", type=Path, help="Font file or directory")

    install_parser = subparsers.add_parser("install", help="Install fonts")
    install_parser.add_argument("source", type=Path, help="Font file or directory")
    install_parser.add_argument(
        "--global",
        action="store_true",
        dest="is_global",
        help="Install for all users. Requires admin privileges.",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing font files.",
    )

    list_parser = subparsers.add_parser("list", help="List installed fonts")
    list_parser.add_argument(
        "--global",
        action="store_true",
        dest="is_global",
        help="List global fonts from HKLM instead of user fonts from HKCU.",
    )

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall fonts")
    uninstall_parser.add_argument(
        "name",
        nargs="?",
        help="Registry font name, e.g. 'Cascadia Mono Bold (TrueType)'",
    )
    uninstall_parser.add_argument(
        "--file",
        type=Path,
        help="Uninstall by installed font filename/path, useful for long TTC registry names.",
    )
    uninstall_parser.add_argument(
        "--global",
        action="store_true",
        dest="is_global",
        help="Uninstall from global fonts. Requires admin privileges.",
    )

    args = parser.parse_args()

    match args.command:
        case "inspect":
            inspect_fonts(args.source)

        case "install":
            install_fonts(args.source, is_global=args.is_global, force=args.force)

        case "list":
            list_installed_fonts(is_global=args.is_global)

        case "uninstall":
            if args.is_global and not is_admin():
                raise SystemExit(
                    "Error: Global font uninstall requires admin privileges."
                )

            if args.file:
                uninstall_by_file(args.file, is_global=args.is_global)
            elif args.name:
                uninstall_by_registry_name(args.name, is_global=args.is_global)
            else:
                raise SystemExit("Error: uninstall requires a registry name or --file.")

        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
