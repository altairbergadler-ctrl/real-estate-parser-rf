"""Command-line adapter for the first local search slice."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from real_estate_parser.application import (
    LocalSearchFailure,
    LocalSearchOperationalError,
    run_local_search,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="real-estate-parser")
    subparsers = parser.add_subparsers(dest="command", required=True)
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--listings", required=True, type=Path)
    search_parser.add_argument("--criteria", required=True, type=Path)
    return parser


def _write_stdout(payload: bytes) -> None:
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def _write_stderr(payload: bytes) -> None:
    sys.stderr.buffer.write(payload)
    sys.stderr.buffer.flush()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse one command and translate application outcomes to CLI contracts."""

    arguments = _parser().parse_args(argv)
    if arguments.command != "search":
        raise RuntimeError("argparse accepted an unknown command")

    listings_path = cast(Path, arguments.listings)
    criteria_path = cast(Path, arguments.criteria)
    try:
        result = run_local_search(listings_path, criteria_path)
    except LocalSearchOperationalError as error:
        _write_stderr(f"{error.role}/{error.reason}\n".encode("ascii"))
        return 2

    if isinstance(result, LocalSearchFailure):
        diagnostics = "".join(
            f"{issue.category}/{issue.code}/{issue.location.json_path}\n" for issue in result.issues
        )
        _write_stderr(diagnostics.encode("ascii"))
        return 1

    _write_stdout(result.json_bytes)
    return 0


__all__ = ["main"]
