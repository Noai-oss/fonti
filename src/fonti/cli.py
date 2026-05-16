from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if sys.platform != "win32":
    raise SystemExit("Error: This tool is only supported on Windows.")

from fonti.windows import is_admin
from fonti.operations import (
    inspect_fonts,
    install_fonts,
    list_installed_fonts,
    uninstall_by_file,
    uninstall_by_filters,
    uninstall_by_registry_name,
)

FONT_FORMATS = ("ttf", "otf", "ttc", "otc")


def parse_font_formats(value: str) -> list[str]:
    """Parse a comma-separated list of font formats for argparse."""
    formats: list[str] = []
    invalid: list[str] = []

    for item in value.split(","):
        font_format = item.strip().lower().removeprefix(".")

        if not font_format:
            continue

        if font_format not in FONT_FORMATS:
            invalid.append(font_format)
            continue

        formats.append(font_format)

    if invalid:
        allowed = ", ".join(FONT_FORMATS)
        raise argparse.ArgumentTypeError(
            f"unsupported font format: {', '.join(invalid)} (choose from: {allowed})"
        )

    if not formats:
        raise argparse.ArgumentTypeError("expected at least one font format")

    return formats


class FontFormatAction(argparse.Action):
    """Collect comma-separated or repeated --format values into one list."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        if not isinstance(values, str):
            raise argparse.ArgumentError(self, f"{option_string} expects a value")

        try:
            parsed_formats = parse_font_formats(values)
        except argparse.ArgumentTypeError as exc:
            raise argparse.ArgumentError(self, str(exc)) from exc

        formats = list(getattr(namespace, self.dest, None) or [])

        for font_format in parsed_formats:
            if font_format not in formats:
                formats.append(font_format)

        setattr(namespace, self.dest, formats)


def add_font_filter_arguments(
    command_parser: argparse.ArgumentParser,
    action: str,
    *,
    include_format: bool = True,
) -> None:
    """Add shared font filtering arguments to a subcommand parser."""
    command_parser.add_argument(
        "--name-regex",
        help=(
            f"Only {action} fonts whose file name, including extension, "
            "or registry name matches this regex. Matching is case-insensitive."
        ),
    )

    if not include_format:
        return

    command_parser.add_argument(
        "--format",
        action=FontFormatAction,
        dest="formats",
        metavar="FORMAT[,FORMAT...]",
        help=(
            f"Only {action} fonts with these formats. Use commas or repeat the option."
        ),
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
    add_font_filter_arguments(install_parser, "install")

    list_parser = subparsers.add_parser("list", help="List installed fonts")
    list_parser.add_argument(
        "--global",
        action="store_true",
        dest="is_global",
        help="List global fonts from HKLM instead of user fonts from HKCU.",
    )
    add_font_filter_arguments(list_parser, "list", include_format=False)

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
        "--yes",
        action="store_true",
        help="Confirm filtered uninstall operations that may remove multiple fonts.",
    )
    add_font_filter_arguments(uninstall_parser, "uninstall", include_format=False)

    args = parser.parse_args()

    match args.command:
        case "inspect":
            inspect_fonts(args.source)

        case "install":
            install_fonts(
                args.source,
                is_global=args.is_global,
                force=args.force,
                name_regex=args.name_regex,
                formats=args.formats,
            )

        case "list":
            list_installed_fonts(
                is_global=args.is_global,
                name_regex=args.name_regex,
            )

        case "uninstall":
            if args.is_global and not is_admin():
                raise SystemExit(
                    "Error: Global font uninstall requires admin privileges."
                )

            has_filters = bool(args.name_regex)
            target_count = sum(
                bool(target) for target in (args.file, args.name, has_filters)
            )

            if target_count > 1:
                raise SystemExit(
                    "Error: Choose only one uninstall target: "
                    "registry name, --file, or filters."
                )

            if has_filters:
                if not args.yes:
                    raise SystemExit(
                        "Error: Filtered uninstall can remove multiple fonts. "
                        "Preview with matching `fonti list` filters, "
                        "then re-run with --yes."
                    )

                uninstall_by_filters(
                    name_regex=args.name_regex,
                    is_global=args.is_global,
                )
            elif args.file:
                uninstall_by_file(args.file, is_global=args.is_global)
            elif args.name:
                uninstall_by_registry_name(args.name, is_global=args.is_global)
            else:
                raise SystemExit(
                    "Error: uninstall requires a registry name, --file, "
                    "or --name-regex."
                )

        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
