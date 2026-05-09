from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.platform != "win32":
    raise SystemExit("Error: This tool is only supported on Windows.")

from fonti.windows import is_admin, relaunch_as_admin
from fonti.operations import (
    inspect_fonts,
    install_fonts,
    list_installed_fonts,
    uninstall_by_file,
    uninstall_by_registry_name,
)


def ensure_global_admin(is_global: bool, elevate: bool, action: str) -> None:
    """Request elevation or fail when a global operation needs admin rights."""
    if not is_global or is_admin():
        return

    if elevate:
        print(f"Requesting administrator privileges for global font {action}...")
        relaunch_as_admin()

    raise SystemExit(
        f"Error: Global font {action} requires admin privileges. "
        "Re-run with --elevate to request UAC permission."
    )


def wait_on_exit() -> None:
    """Keep an elevated console window open until the user is ready."""
    try:
        input("\nPress Enter to close this window...")
    except EOFError:
        pass


def main() -> None:
    """CLI entry point. Parses arguments and routes to operations."""
    parser = argparse.ArgumentParser(
        prog="fonti",
        description="A command-line font installer for Windows.",
    )
    parser.add_argument("--wait-on-exit", action="store_true", help=argparse.SUPPRESS)

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
    install_parser.add_argument(
        "--elevate",
        action="store_true",
        help="Request UAC elevation when using --global.",
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
    uninstall_parser.add_argument(
        "--elevate",
        action="store_true",
        help="Request UAC elevation when using --global.",
    )

    args = parser.parse_args()

    try:
        match args.command:
            case "inspect":
                inspect_fonts(args.source)

            case "install":
                ensure_global_admin(args.is_global, args.elevate, "installation")
                install_fonts(args.source, is_global=args.is_global, force=args.force)

            case "list":
                list_installed_fonts(is_global=args.is_global)

            case "uninstall":
                ensure_global_admin(args.is_global, args.elevate, "uninstallation")

                if args.file:
                    uninstall_by_file(args.file, is_global=args.is_global)
                elif args.name:
                    uninstall_by_registry_name(args.name, is_global=args.is_global)
                else:
                    raise SystemExit(
                        "Error: uninstall requires a registry name or --file."
                    )

            case _:
                parser.print_help()
    finally:
        if args.wait_on_exit:
            wait_on_exit()


if __name__ == "__main__":
    main()
