# ruff: noqa: W291
"""Optional local check: bundled standard.json against an authoritative FIELDS source.

The source file is intentionally not part of the repository. Place it at
``tests/standard.fields.txt`` locally when you want the exact source-to-JSON
round-trip check.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any, cast

from dipworkpy.tools.fields_to_json import parse_fields_text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STANDARD_JSON = PROJECT_ROOT / "dipworkpy/geography/map/data/standard.json"
FIELDS_SOURCE = PROJECT_ROOT / "tests/standard.fields.txt"


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _borders_by_key(data: dict[str, Any]) -> dict[str, list[str]]:
    return {
        f"{field_name}:{neighbor}": units
        for field_name, field in data["fields"].items()
        for neighbor, units in field.get("borders", {}).items()
    }


def _boundary_check_lines(parsed: dict[str, Any], bundled: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    parsed_borders = _borders_by_key(parsed)
    bundled_borders = _borders_by_key(bundled)
    for border_key in sorted(parsed_borders):
        expected = parsed_borders[border_key]
        actual = bundled_borders.get(border_key)
        if actual == expected:
            lines.append(f"FIELDS border {border_key}: OK units={expected}")
        else:
            lines.append(f"FIELDS border {border_key}: DIFF expected={expected!r} actual={actual!r}")
    missing_from_fields = sorted(set(bundled_borders) - set(parsed_borders))
    for border_key in missing_from_fields:
        lines.append(f"FIELDS border {border_key}: EXTRA_IN_JSON actual={bundled_borders[border_key]!r}")
    return lines


def _should_emit_boundary_checks(pytestconfig: Any) -> bool:
    verbose = int(pytestconfig.getoption("verbose", default=0) or 0)
    debug = pytestconfig.getoption("debug", default=None)
    return verbose > 0 or bool(debug)


def test_boundary_check_lines_include_every_border() -> None:
    parsed = {"fields": {"A": {"borders": {"B": ["A"]}}, "B": {"borders": {"C": ["F"]}}}}
    bundled = {"fields": dict(parsed["fields"])}

    assert _boundary_check_lines(parsed, bundled) == [
        "FIELDS border A:B: OK units=['A']",
        "FIELDS border B:C: OK units=['F']",
    ]


def test_standard_json_matches_local_fields_source(pytestconfig: Any, capsys: Any) -> None:
    if not FIELDS_SOURCE.exists():
        pytest.skip(f"local authoritative FIELDS source not present: {FIELDS_SOURCE}")

    parsed = parse_fields_text(FIELDS_SOURCE.read_text(encoding="latin-1"))
    bundled = _load_json(STANDARD_JSON)

    if _should_emit_boundary_checks(pytestconfig):
        with capsys.disabled():
            for line in _boundary_check_lines(parsed, bundled):
                print(line)

    assert bundled["map_id"] == parsed["map_id"]
    assert bundled["units"] == parsed["units"]
    assert bundled["fields"] == parsed["fields"]
