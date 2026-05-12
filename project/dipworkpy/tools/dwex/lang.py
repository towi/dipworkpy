"""DDL parser - line-based, block-oriented.

Grammar (loose):
    @dwex
    title: ...
    desc:  ...
    map { <field-lines> <edge-lines> }
    orders { <order-lines> }
    pattfields { <names> }
    note { ... }
    @end
"""
from __future__ import annotations

import re
from typing import List, Tuple

from dipworkpy.tools.dwex.model import (
    DwexDocument, DwexEdge, DwexField, DwexOrderSpec, DwexUnit,
)


class DwexParseError(ValueError):
    """Raised when the .dwex source fails to parse."""


_FIELD_RE = re.compile(r"^(\w+)\s+(\w+)\s+(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$")
_EDGE_RE = re.compile(r"^(\w+)\s+--([A-Z]*)\s+(\w+)$")
_ORDER_RE = re.compile(
    r"^(\w+)\s+(\w)\s+(\w+)\s+(hld|mve|hsup|msup|con)(?:\s+(\w+))?\s*([!>]*)$"
)


def _strip_inline_comment(line: str) -> str:
    return re.sub(r"\s+#.*$", "", line).strip()


def _passability_for_modifier(mod: str) -> Tuple[str, str, str]:
    """Translate edge modifier suffix into (army, fleet, convoy_move) values."""
    mod = mod.upper()
    if mod == "" or mod == "AF":
        return ("ja", "ja", "ja")
    if mod == "A":
        return ("ja", "nein", "nein")
    if mod == "F":
        return ("nein", "ja", "ja")
    if mod == "C":
        return ("nein", "nein", "ja")
    raise DwexParseError(f"unknown edge modifier: --{mod}")


def _extract_block(text: str, block: str) -> str:
    pat = re.compile(rf"{block}\s*\{{(.*?)\}}", re.DOTALL)
    m = pat.search(text)
    return m.group(1) if m else ""


def parse(text: str) -> DwexDocument:
    if "@dwex" not in text or "@end" not in text:
        raise DwexParseError("missing @dwex / @end markers")

    lines = [_strip_inline_comment(ln) for ln in text.splitlines()]
    joined = "\n".join(lines)

    title_m = re.search(r"^title:\s*(.+)$", joined, re.MULTILINE)
    if not title_m:
        raise DwexParseError("missing title:")
    title = title_m.group(1).strip()

    desc_m = re.search(r"^desc:\s*(.+)$", joined, re.MULTILINE)
    description = desc_m.group(1).strip() if desc_m else ""

    fields: List[DwexField] = []
    edges: List[DwexEdge] = []
    map_body = _extract_block(joined, "map")
    for raw in map_body.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        fm = _FIELD_RE.match(ln)
        em = _EDGE_RE.match(ln)
        if fm:
            fields.append(DwexField(
                name=fm.group(1), type=fm.group(2),
                x=float(fm.group(3)), y=float(fm.group(4)),
            ))
        elif em:
            a, mod, b = em.group(1), em.group(2), em.group(3)
            army, fleet, conv = _passability_for_modifier(mod)
            edges.append(DwexEdge(a=a, b=b, army=army, fleet=fleet, convoy_move=conv))
        else:
            raise DwexParseError(f"unparsable map line: {ln!r}")

    orders: List[DwexOrderSpec] = []
    orders_body = _extract_block(joined, "orders")
    for raw in orders_body.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        om = _ORDER_RE.match(ln)
        if not om:
            raise DwexParseError(f"unparsable order line: {ln!r}")
        nat, utype, current, order, dest, marks = om.groups()
        orders.append(DwexOrderSpec(
            nation=nat, utype=utype, current=current,
            order=order, dest=dest,
            expected_failed=("!" in (marks or "")),
            expected_dislodged=(">" in (marks or "")),
        ))

    units = [DwexUnit(nation=o.nation, utype=o.utype, current=o.current) for o in orders]

    pattfields_body = _extract_block(joined, "pattfields")
    expected_pattfields = {
        tok for raw in pattfields_body.splitlines() for tok in raw.split()
    }

    return DwexDocument(
        title=title, description=description,
        fields=fields, edges=edges, units=units, orders=orders,
        expected_pattfields=expected_pattfields,
    )


def parse_file(path) -> DwexDocument:
    from pathlib import Path
    return parse(Path(path).read_text())
