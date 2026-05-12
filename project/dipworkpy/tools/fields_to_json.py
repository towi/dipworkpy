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


def parse_fields_text(text: str) -> Dict[str, Any]:
    fields: Dict[str, dict] = {}
    edges: Dict[str, dict] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        if line.startswith("#"):
            parts = line[1:].split()
            if len(parts) < 5:
                continue
            name, x, y, sub_of, ftype = parts[0], parts[1], parts[2], parts[3], parts[4]
            field: Dict[str, Any] = {"type": ftype, "pos": [int(x), int(y)]}
            if sub_of and sub_of != "-":
                field["sub_of"] = sub_of
            if len(parts) >= 6 and parts[5] == "1":
                field["is_supply_center"] = True
            if len(parts) >= 7:
                field["home_of"] = parts[6]
            fields[name] = field
        elif line.startswith("-"):
            parts = line[1:].split()
            if len(parts) < 5:
                continue
            frm, to, army, fleet, convoy = parts[0], parts[1], parts[2], parts[3], parts[4]
            edges[f"{frm}:{to}"] = {"army": army, "fleet": fleet, "convoy_move": convoy}
    return {"map_id": "standard", "fields": fields, "edges": edges}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    raw = args.input.read_text(encoding="latin-1")
    data = parse_fields_text(raw)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True))
    print(f"wrote {len(data['fields'])} fields, {len(data['edges'])} edges to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
