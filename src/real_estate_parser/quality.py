"""Portable quality-check entry point for repository development."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QualityStage:
    """One read-only quality check executed from the project root."""

    name: str
    arguments: tuple[str, ...]


def _project_root() -> Path:
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("quality must run inside the project tree")


def _stages() -> tuple[QualityStage, ...]:
    python = sys.executable
    return (
        QualityStage("ruff format check", (python, "-m", "ruff", "format", "--check", ".")),
        QualityStage("ruff lint", (python, "-m", "ruff", "check", ".")),
        QualityStage("mypy strict", (python, "-m", "mypy")),
        QualityStage(
            "pytest",
            (python, "-m", "pytest", "--ignore=tests/test_fixture_catalog.py"),
        ),
        QualityStage(
            "fixture catalog integrity",
            (python, "-m", "pytest", "tests/test_fixture_catalog.py"),
        ),
    )


def main() -> int:
    """Run every repository quality stage and stop at the first failure."""

    try:
        project_root = _project_root()
    except RuntimeError as error:
        print(f"[quality] FAILED: setup: {error}", file=sys.stderr)
        return 2

    for stage in _stages():
        print(f"[quality] START: {stage.name}", flush=True)
        try:
            completed = subprocess.run(stage.arguments, cwd=project_root, check=False)
        except OSError as error:
            print(f"[quality] FAILED: {stage.name}: {error}", file=sys.stderr)
            return 2
        if completed.returncode != 0:
            print(
                f"[quality] FAILED: {stage.name} (exit code {completed.returncode})",
                file=sys.stderr,
            )
            return completed.returncode
        print(f"[quality] PASS: {stage.name}", flush=True)

    print("[quality] PASS: all stages", flush=True)
    return 0
