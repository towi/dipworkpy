"""InlineMap - MapProtocol implementation from an in-memory MapDefinition.

Used by DDL test fixtures and custom variant requests.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple, Union

from dipworkpy.geo_model import Edge, FieldType, MapDefinition, Passable


class InlineMap:
    def __init__(self, mdef: MapDefinition, map_id: str = "inline") -> None:
        self.map_id = map_id
        self._mdef = mdef
        self._subfields_by_super: Dict[str, List[str]] = {}
        for name, fd in mdef.fields.items():
            if fd.sub_of:
                self._subfields_by_super.setdefault(fd.sub_of, []).append(name)

    def field_exists(self, fld: str) -> bool:
        return fld in self._mdef.fields

    def field_type(self, fld: str) -> FieldType:
        return self._mdef.fields[fld].type

    def superfield_of(self, fld: str) -> str:
        fd = self._mdef.fields[fld]
        return fd.sub_of or fld

    def subfields_of(self, fld: str) -> List[str]:
        return list(self._subfields_by_super.get(fld, []))

    def is_supply_center(self, fld: str) -> bool:
        return self._mdef.fields[fld].is_supply_center

    def home_center_of(self, fld: str) -> Optional[str]:
        return self._mdef.fields[fld].home_of

    def neighbor_order(self, fld: str) -> List[str]:
        explicit = self._mdef.fields[fld].neighbor_order
        if explicit:
            return list(explicit)
        return [to for (frm, to) in self._mdef.edges if frm == fld]

    def diversion(self, frm: str, to: str, utype: str) -> Optional[str]:
        field = self._mdef.fields.get(frm)
        if field is None:
            return None
        return field.diversions.get(to, {}).get(utype)

    def edge(self, frm: str, to: str) -> Optional[Edge]:
        return self._mdef.edges.get((frm, to))

    def edge_items(self) -> List[Tuple[str, str, Edge]]:
        return [(frm, to, edge) for (frm, to), edge in self._mdef.edges.items()]

    def neighbors(self, fld: str) -> Set[str]:
        return {to for (frm, to) in self._mdef.edges if frm == fld}

    def army_passable(self, frm: str, to: str) -> bool:
        e = self.edge(frm, to)
        if e is None:
            return False
        return e.army == Passable.YES

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
