"""Convoy-graph extraction and cmove classification (GEO-009)."""

from __future__ import annotations

from collections import deque
from typing import Iterable, List, Set, Tuple

from dipworkpy.geo_model import ConvoyGraph, FieldType
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.geography.rules import can_reach_by_unit
from dipworkpy.model import Order, OrderType


def _convoyer_fields(orders: List[Order]) -> Set[str]:
    return {o.current for o in orders if o.order == OrderType.con}


def _convoy_graph_edges(convoyers: Set[str], m: MapProtocol) -> tuple[Set[Tuple[str, str]], Set[Tuple[str, str]]]:
    sea_edges: Set[Tuple[str, str]] = set()
    coastal_edges: Set[Tuple[str, str]] = set()

    for sea in convoyers:
        if not m.field_exists(sea) or m.field_type(sea) != FieldType.O:
            continue
        for nb in m.neighbors(sea):
            if not m.field_exists(nb) or not m.convoy_passable(sea, nb):
                continue
            if m.field_type(nb) == FieldType.O:
                if nb in convoyers:
                    pair = tuple(sorted([sea, nb]))
                    sea_edges.add((pair[0], pair[1]))
            else:
                coast = m.superfield_of(nb)
                coastal_edges.add((sea, coast))
                coastal_edges.add((coast, sea))
    for frm, to, _edge in m.edge_items():
        if not m.field_exists(frm) or not m.field_exists(to):
            continue
        if not m.convoy_passable(frm, to):
            continue
        frm_super = m.superfield_of(frm)
        to_super = m.superfield_of(to)
        if frm in convoyers and m.field_type(frm) == FieldType.O and m.field_type(to_super) != FieldType.O:
            coastal_edges.add((frm, to_super))
            coastal_edges.add((to_super, frm))
        elif to in convoyers and m.field_type(to) == FieldType.O and m.field_type(frm_super) != FieldType.O:
            coastal_edges.add((to, frm_super))
            coastal_edges.add((frm_super, to))
    return sea_edges, coastal_edges


def _adjacent(node: str, edges: Iterable[Tuple[str, str]]) -> Set[str]:
    out: Set[str] = set()
    for a, b in edges:
        if a == node:
            out.add(b)
        elif b == node:
            out.add(a)
    return out


def convoy_route_exists(start: str, dest: str, graph: ConvoyGraph) -> bool:
    """Return whether the extracted graph connects coast -> convoyers -> coast."""
    edges = graph.sea_edges | graph.coastal_edges
    allowed = graph.convoyer_fields | {start, dest}
    queue: deque[str] = deque([start])
    seen = {start}
    while queue:
        node = queue.popleft()
        if node == dest:
            return True
        for nb in _adjacent(node, edges):
            if nb in allowed and nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return False


def convoy_route_uses(start: str, dest: str, required: str, graph: ConvoyGraph) -> bool:
    """Return whether a route exists that includes the required convoyer."""
    if required not in graph.convoyer_fields:
        return False
    return convoy_route_exists(start, required, graph) and convoy_route_exists(required, dest, graph)


def classify_cmove_candidates(orders: List[Order], m: MapProtocol) -> Set[int]:
    """Indices of army moves for which ordered convoyers form a route.

    B.3.2.14 sentence 3: unflagged moves whose destination is directly
    reachable by land are NOT candidates -- they move by land and ignore
    any ordered convoy route.
    """
    convoyed_starts = {
        m.superfield_of(o.dest) for o in orders if o.order == OrderType.con and o.dest and m.field_exists(o.dest)
    }
    convoyers = _convoyer_fields(orders)
    sea_edges, coastal_edges = _convoy_graph_edges(convoyers, m)
    graph = ConvoyGraph(
        sea_edges=sea_edges,
        coastal_edges=coastal_edges,
        convoyer_fields=convoyers,
        cmove_candidates=set(),
    )

    cmoves: Set[int] = set()
    for i, o in enumerate(orders):
        if (
            o.order == OrderType.mve
            and o.utype == "A"
            and m.field_exists(o.current)
            and m.superfield_of(o.current) in convoyed_starts
            and o.dest
            and m.field_exists(o.dest)
            and convoy_route_exists(m.superfield_of(o.current), m.superfield_of(o.dest), graph)
            # B.3.2.14 sentence 3: an unflagged mve to a directly reachable
            # (adjacent) field is a land move; ordered convoy routes are
            # ignored. Only the explicit "mve [Convoy]" flag (GEO-010) makes it
            # a convoy move. Unflagged non-adjacent moves stay candidates --
            # the convoy is their only way to reach the destination.
            and (o.via_convoy or not can_reach_by_unit(o.current, o.dest, o.utype, m))
        ):
            cmoves.add(i)
    return cmoves


def build_convoy_graph(orders: List[Order], m: MapProtocol) -> ConvoyGraph:
    convoyers = _convoyer_fields(orders)
    sea_edges, coastal_edges = _convoy_graph_edges(convoyers, m)

    return ConvoyGraph(
        sea_edges=sea_edges,
        coastal_edges=coastal_edges,
        convoyer_fields=convoyers,
        cmove_candidates=classify_cmove_candidates(orders, m),
    )
