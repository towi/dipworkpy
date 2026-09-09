"""Convert a FIELDS-spec text file to the canonical standard.json schema.

CLI usage:
    python -m dipworkpy.tools.fields_to_json input.txt output.json

The FIELDS-spec format is line-based; each non-comment line is either a
field definition or an edge. Format (loosely):
    # <name> <x> <y> <sub_of-or-dash> <type> <sp> <home>
    - <from> <to> <army> <fleet> <convoy>

Lines starting with ``%`` are comments. Whitespace is flexible.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def _features_for_type(ftype: str) -> list[str]:
    if ftype == "O":
        return ["sea", "sea_or_coast", "$convoying"]
    if ftype in {"LC", "LCA", "LCB", "LCF"}:
        return ["land", "coast", "sea_or_coast", "$convoyable"]
    if ftype in {"L", "LA"}:
        return ["land"]
    return []


def _can_build_for_type(ftype: str) -> list[str]:
    if ftype == "LA":
        return ["A"]
    if ftype == "LCB":
        return ["A", "F"]
    if ftype == "LCA":
        return ["A"]
    if ftype == "LCF":
        return ["F"]
    return []


def parse_fields_text(text: str) -> Dict[str, Any]:
    fields: Dict[str, dict] = {}
    raw_edges: list[tuple[str, str, str, str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        if line.startswith("#"):
            parts = line[1:].split()
            if len(parts) < 5:
                continue
            name, x, y, sub_of, ftype = parts[0], parts[1], parts[2], parts[3], parts[4]
            field: Dict[str, Any] = {
                "type": ftype,
                "pos": [int(x), int(y)],
                "features": _features_for_type(ftype),
                "can_build": _can_build_for_type(ftype),
                "borders": {},
                "neighbor_order": [],
            }
            if sub_of and sub_of != "-":
                field["sub_of"] = sub_of
            if len(parts) >= 6 and parts[5] == "1":
                field["is_supply_center"] = True
                field["supply_center_value"] = 1
            if len(parts) >= 7:
                field["home_of"] = parts[6]
            fields[name] = field
        elif line.startswith("-"):
            parts = line[1:].split()
            if len(parts) < 5:
                continue
            frm, to, army, fleet, convoy = parts[0], parts[1], parts[2], parts[3], parts[4]
            raw_edges.append((frm, to, army, fleet, convoy))

    for name, field in fields.items():
        subfields = [sub for sub, candidate in fields.items() if candidate.get("sub_of") == name]
        if subfields:
            field["subfields"] = subfields

    for frm, to, army, fleet, _convoy in raw_edges:
        if frm not in fields:
            continue
        fields[frm]["neighbor_order"].append(to)
        units: list[str] = []
        if army == "ja":
            units.append("A")
        if fleet == "ja":
            units.append("F")
        if _convoy == "ja":
            units.append("$convoy")
        if units:
            fields[frm]["borders"][to] = units
        if to in fields and fields[to].get("subfields"):
            if fleet not in {"ja", "nein", "-"}:
                fields[frm].setdefault("diversions", {}).setdefault(to, {})["F"] = "$imp" if fleet == "imp" else fleet

    return {
        "map_id": "standard",
        "units": {"A": {"requires": ["land"]}, "F": {"requires": ["sea_or_coast"]}},
        "fields": fields,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    raw = args.input.read_text(encoding="latin-1")
    data = parse_fields_text(raw)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True))
    border_count = sum(len(field.get("borders", {})) for field in data["fields"].values())
    print(f"wrote {len(data['fields'])} fields, {border_count} borders to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
