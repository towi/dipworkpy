"""DDL -> InlineMap / MapDefinition."""
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


def to_map_definition(doc: DwexDocument) -> MapDefinition:
    """Build a MapDefinition from a parsed DDL document.

    Field type strings must be valid FieldType enum values (LA, LCB, LCA,
    LCF, LC, L, O, COL). Edge modifiers are mapped to Passable values via
    _pass; subfield-required values pass through as strings unchanged.
    """
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
    return MapDefinition(fields=fields, edges=edges)


def to_inline_map(doc: DwexDocument) -> InlineMap:
    """Build an InlineMap from a parsed DDL document. Backward-compat wrapper."""
    return InlineMap(to_map_definition(doc), map_id="dwex_inline")
