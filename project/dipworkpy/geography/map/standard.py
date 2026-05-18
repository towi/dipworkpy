"""StandardMap - loads the bundled standard.json and exposes MapProtocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, cast

from dipworkpy.geo_model import Edge, FieldType, Passable

_DATA_FILE = Path(__file__).parent / "data" / "standard.json"


class StandardMap:
    """Loads the standard map data and serves it through MapProtocol."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.map_id = "standard"
        src = path or _DATA_FILE
        with open(src) as f:
            raw = json.load(f)
        self._fields: Dict[str, dict] = raw["fields"]
        # Edges keyed by (from, to). Preferred JSON stores borders inside each
        # field; ordered edge arrays and legacy "from:to" objects are accepted.
        self._edges: Dict[Tuple[str, str], Edge] = {}
        raw_edges = raw.get("edges")
        if raw_edges is None:
            for frm, field in self._fields.items():
                for to, units in field.get("borders", {}).items():
                    self._edges[(frm, to)] = Edge(
                        army=Passable.YES if "A" in units else Passable.NO,
                        fleet=Passable.YES if "F" in units else Passable.NO,
                        convoy_move=Passable.YES if "$convoy" in units else Passable.NO,
                    )
        elif isinstance(raw_edges, list):
            for val in raw_edges:
                frm = val["from"]
                to = val["to"]
                self._edges[(frm, to)] = Edge(
                    army=val["army"],
                    fleet=val["fleet"],
                    convoy_move=val["convoy_move"],
                )
        else:
            for key, val in raw_edges.items():
                frm, to = key.split(":", 1)
                self._edges[(frm, to)] = Edge(**val)
        # Pre-compute subfield reverse index
        self._subfields_by_super: Dict[str, List[str]] = {}
        for name, fdef in self._fields.items():
            sub_of = fdef.get("sub_of")
            if sub_of:
                self._subfields_by_super.setdefault(sub_of, []).append(name)

    def field_exists(self, fld: str) -> bool:
        return fld in self._fields

    def field_type(self, fld: str) -> FieldType:
        return FieldType(self._fields[fld]["type"])

    def superfield_of(self, fld: str) -> str:
        return self._fields[fld].get("sub_of") or fld

    def subfields_of(self, fld: str) -> List[str]:
        return list(self._subfields_by_super.get(fld, []))

    def is_supply_center(self, fld: str) -> bool:
        return bool(self._fields[fld].get("is_supply_center", False))

    def home_center_of(self, fld: str) -> Optional[str]:
        return self._fields[fld].get("home_of")

    def neighbor_order(self, fld: str) -> List[str]:
        explicit = self._fields[fld].get("neighbor_order")
        if explicit:
            return list(explicit)
        return [to for (frm, to) in self._edges if frm == fld]

    def diversion(self, frm: str, to: str, utype: str) -> Optional[str]:
        return cast(Optional[str], self._fields.get(frm, {}).get("diversions", {}).get(to, {}).get(utype))

    def edge(self, frm: str, to: str) -> Optional[Edge]:
        return self._edges.get((frm, to))

    def edge_items(self) -> List[Tuple[str, str, Edge]]:
        return [(frm, to, edge) for (frm, to), edge in self._edges.items()]

    def neighbors(self, fld: str) -> Set[str]:
        return {to for (frm, to) in self._edges if frm == fld}

    def army_passable(self, frm: str, to: str) -> bool:
        e = self.edge(frm, to)
        if e is None:
            return False
        if e.army == Passable.YES:
            return True
        # Literal subfield-name strings (coast-required) also count as passable
        return isinstance(e.army, str) and e.army not in {
            Passable.NO.value,
            Passable.NA.value,
            Passable.IMP.value,
            Passable.YES.value,
        }

    def fleet_passable(self, frm: str, to: str) -> Union[Passable, str]:
        e = self.edge(frm, to)
        if e is None:
            return Passable.NA
        return e.fleet

    def convoy_passable(self, frm: str, to: str) -> bool:
        e = self.edge(frm, to)
        if e is None:
            return False
        return e.convoy_move == Passable.YES
