"""Provide D2L workbook, local validation, and supplied-client scan commands."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import get_args

from .d2l.client import ProviderUnavailable, create_client
from .d2l.config import ConfigurationError, load_settings
from .d2l.content import scan_courses
from .d2l.courses import InventoryError
from .d2l.extract_course_urls import ExtractionError, extract_course_urls
from .d2l.models import SearchMode, ToolKey
from .d2l.reports import ReportWriter
from .d2l.validation import validate_inputs


class _ArgumentParser(argparse.ArgumentParser):
    """Keep rejected argument values out of diagnostics."""

    def error(self, message: str) -> None:
        """Print usage without echoing rejected options or values."""
        self.print_usage(sys.stderr)
        self.exit(
            2, "Invalid command arguments. Use --help for supported options.\n"
        )


def _parser() -> argparse.ArgumentParser:
    """Construct the published command hierarchy without executing work."""
    parser = _ArgumentParser(
        prog="gc-stem", description=__doc__, allow_abbrev=False
    )
    top = parser.add_subparsers(dest="service", required=True)
    d2l = top.add_parser("d2l", help="D2L workbook and search tools")
    commands = d2l.add_subparsers(dest="command", required=True)
    courses = commands.add_parser("courses", help="Prepare course inventories")
    course_commands = courses.add_subparsers(
        dest="course_command", required=True
    )
    extract = course_commands.add_parser(
        "extract-urls", help="Copy workbook hyperlinks"
    )
    extract.add_argument("--source", type=Path, required=True)
    extract.add_argument("--destination", type=Path, required=True)
    extract.add_argument("--sheet", default="D2L")
    extract.add_argument("--name-column", default="D2l_course_name")
    extract.add_argument("--url-column", default="CourseURL")
    extract.add_argument("--overwrite", action="store_true")
    search = commands.add_parser(
        "search", help="Validate or scan authored scope"
    )
    search.add_argument("--config", type=Path, help="TOML path, or D2L_CONFIG")
    search.add_argument(
        "--validate-only", action="store_true", help="Check local inputs"
    )
    search.add_argument(
        "--term", action="append", help="Replace configured terms; repeatable"
    )
    search.add_argument("--tool", action="append", choices=get_args(ToolKey))
    search.add_argument("--courses", type=Path)
    search.add_argument("--courses-format", choices=("csv", "xlsx"))
    search.add_argument("--sheet")
    search.add_argument("--name-column")
    search.add_argument("--url-column")
    search.add_argument("--id-column")
    search.add_argument("--output", type=Path)
    search.add_argument("--mode", choices=get_args(SearchMode))
    search.add_argument(
        "--case-sensitive", action="store_const", const=False, default=None
    )
    return parser


def _search(
    arguments: argparse.Namespace, environment: Mapping[str, str]
) -> int:
    """Validate local inputs and invoke an explicitly available provider."""
    overrides: dict[str, object] = {}
    for argument, key in (
        ("term", "search.terms"),
        ("tool", "crawl.tools"),
        ("courses", "courses.file"),
        ("courses_format", "courses.format"),
        ("sheet", "courses.sheet"),
        ("name_column", "courses.name_column"),
        ("url_column", "courses.url_column"),
        ("id_column", "courses.id_column"),
        ("output", "output.directory"),
        ("mode", "search.mode"),
        ("case_sensitive", "search.ignore_case"),
    ):
        value = getattr(arguments, argument)
        if value is not None:
            overrides[key] = value
    settings = load_settings(arguments.config, overrides, environment)
    prepared = validate_inputs(settings)
    if arguments.validate_only:
        print(
            "Local validation succeeded: "
            f"{len(prepared.inventory.courses)} courses, "
            f"{len(prepared.plan.targets)} targets, "
            f"{len(settings.crawl.tools)} tools."
        )
        return 0
    client = create_client(settings)
    try:
        writer = ReportWriter(
            settings,
            prepared.inventory,
            client_info=client.info,
            plan=prepared.plan,
        )
    except Exception:
        client.close()
        raise
    result = scan_courses(settings, prepared.inventory, client, writer)
    print(f"Run state: {result.state}")
    for path in result.saved_paths:
        print(path)
    if result.diagnostics:
        print(
            "Diagnostics: "
            + ", ".join(item["code"] for item in result.diagnostics),
            file=sys.stderr,
        )
    return result.exit_code


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> int:
    """Run one command and return a documented process exit code.

    Args:
        argv: Arguments excluding the executable; defaults to process argv.
        environment: Optional controlled environment for configuration/tests.

    Returns:
        0 for local success/complete scan, 1 for run/output failure, 2 for
        invalid input/unavailable feature, 3 for partial coverage, or 130 for
        cancellation. Argument parsing/help uses normal argparse SystemExit.

    Expected diagnostics omit rejected values and exception bodies. Live scan
    remains unavailable until create_client() supplies a verified provider.
    """
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "courses":
            result = extract_course_urls(
                arguments.source,
                arguments.destination,
                sheet_name=arguments.sheet,
                name_column=arguments.name_column,
                url_column=arguments.url_column,
                overwrite=arguments.overwrite,
            )
            print(
                f"Saved {result.copied_count} course URLs "
                f"to {result.destination_path}"
            )
            return 0
        return _search(
            arguments, os.environ if environment is None else environment
        )
    except ProviderUnavailable:
        print(
            "Live scanning requires the SNHU browser provider "
            "and tool adapters. This build supports local --validate-only "
            "and injected-client library scans.",
            file=sys.stderr,
        )
        return 2
    except (
        ConfigurationError,
        InventoryError,
        ExtractionError,
        FileNotFoundError,
        FileExistsError,
    ) as error:
        print(f"Input validation failed: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Canceled.", file=sys.stderr)
        return 130
    except OSError:
        print("Output or local file operation failed.", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Command failed: {type(error).__name__}.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
