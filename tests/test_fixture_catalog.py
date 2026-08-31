from __future__ import annotations

import codecs
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
MANIFEST = FIXTURE_ROOT / "MANIFEST.md"
REGISTERED_INVALID_JSON = FIXTURE_ROOT / "invalid" / "syntax-truncated.json"
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")


def _fixture_json_files() -> tuple[Path, ...]:
    return tuple(sorted(FIXTURE_ROOT.rglob("*.json")))


def _read_utf8(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    assert not data.startswith(codecs.BOM_UTF8), f"UTF-8 BOM is forbidden: {path}"
    return data, data.decode("utf-8")


def _manifest_local_targets() -> tuple[Path, ...]:
    manifest_text = MANIFEST.read_text(encoding="utf-8")
    targets: list[Path] = []
    for match in MARKDOWN_LINK.finditer(manifest_text):
        target = match.group("target").split("#", maxsplit=1)[0]
        if urlsplit(target).scheme:
            continue
        targets.append((MANIFEST.parent / target).resolve())
    return tuple(sorted(set(targets)))


@pytest.mark.parametrize("path", _fixture_json_files(), ids=lambda path: path.name)
def test_fixture_json_is_utf8_without_bom(path: Path) -> None:
    _read_utf8(path)


@pytest.mark.parametrize(
    "path",
    tuple(path for path in _fixture_json_files() if path != REGISTERED_INVALID_JSON),
    ids=lambda path: path.name,
)
def test_registered_valid_json_parses(path: Path) -> None:
    _, text = _read_utf8(path)
    json.loads(text)


def test_registered_invalid_json_does_not_parse() -> None:
    _, text = _read_utf8(REGISTERED_INVALID_JSON)
    with pytest.raises(json.JSONDecodeError):
        json.loads(text)


@pytest.mark.parametrize("target", _manifest_local_targets(), ids=lambda path: path.name)
def test_every_manifest_path_exists(target: Path) -> None:
    assert target.is_file(), f"manifest target does not exist: {target}"


def test_manifest_accounts_for_every_fixture_json() -> None:
    fixture_json = {path.resolve() for path in _fixture_json_files()}
    manifest_json = {path for path in _manifest_local_targets() if path.suffix == ".json"}
    assert manifest_json == fixture_json


@pytest.mark.parametrize(
    "path",
    tuple(sorted((FIXTURE_ROOT / "expected").glob("search-*.json"))),
    ids=lambda path: path.name,
)
def test_search_golden_has_canonical_json_bytes(path: Path) -> None:
    actual, text = _read_utf8(path)
    document = json.loads(text)
    canonical = (
        json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert actual == canonical
