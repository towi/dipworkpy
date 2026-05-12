"""Convoy-graph extraction and cmove classification (GEO-009)."""
from __future__ import annotations

from typing import List, Set, Tuple

from dipworkpy.geo_model import ConvoyGraph, FieldType
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order, OrderType


def _convoyer_fields(orders: List[Order]) -> Set[str]:
    return {o.current for o in orders if o.order == OrderType.con}


def classify_cmove_candidates(orders: List[Order], m: MapProtocol) -> Set[int]:
    """Indices of mve orders that have a matching con order keyed on current."""
    convoyed_starts: Set[str] = set()
    for o in orders:
        if o.order == OrderType.con and o.dest:
            convoyed_starts.add(o.dest)
    cmoves: Set[int] = set()
    for i, o in enumerate(orders):
        if o.order == OrderType.mve and o.current in convoyed_starts:
            cmoves.add(i)
    return cmoves


def build_convoy_graph(orders: List[Order], m: MapProtocol) -> ConvoyGraph:
    convoyers = _convoyer_fields(orders)
    sea_edges: Set[Tuple[str, str]] = set()
    coastal_edges: Set[Tuple[str, str]] = set()

    # Build sea-sea and sea-coast adjacencies relevant for convoy.
    for sea in convoyers:
        if not m.field_exists(sea) or m.field_type(sea) != FieldType.O:
            continue
        for nb in m.neighbors(sea):
            if not m.field_exists(nb):
                continue
            t = m.field_type(nb)
            if t == FieldType.O and nb in convoyers:
                pair = tuple(sorted([sea, nb]))
                sea_edges.add((pair[0], pair[1]))
            elif t in {FieldType.LCB, FieldType.LC, FieldType.LCA, FieldType.LCF}:
                coastal_edges.add((sea, nb))
                coastal_edges.add((nb, sea))

    return ConvoyGraph(
        sea_edges=sea_edges,
        coastal_edges=coastal_edges,
        convoyer_fields=convoyers,
        cmove_candidates=classify_cmove_candidates(orders, m),
    )
