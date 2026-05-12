"""DDL -> InlineMap."""
from __future__ import annotations

from dipworkpy.geo_model import (
    Edge, FieldDef, FieldType, MapDefinition, Passable,
)
from dipworkpy.geography.map.inline import InlineMap
from dipworkpy.tools.dwex.model import DwexDocument


def _pass(val: str):
    try:
        return Passable(val)
    except ValueError:
        # could be a subfield name (coast-required); pass through as str
        return val


def to_inline_map(doc: DwexDocument) -> InlineMap:
    fields = {}
    for f in doc.fields:
        fields[f.name] = FieldDef(
            name=f.name, type=FieldType(f.type),
            sub_of=f.sub_of, pos=(f.x, f.y),
        )
    edges = {}
    for e in doc.edges:
        ed = Edge(army=_pass(e.army), fleet=_pass(e.fleet),
                  convoy_move=_pass(e.convoy_move))
        edges[(e.a, e.b)] = ed
        if not e.directed:
            edges[(e.b, e.a)] = ed
    return InlineMap(MapDefinition(fields=fields, edges=edges), map_id="dwex_inline")
