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


def classify_cmove_candidates(orders: List[Order], m: MapProtocol, via_explicit: bool = False) -> Set[int]:
    """Indices of moves the order pre-processor / geography hands to the
    conflicter as convoy moves (cmve / cmove_candidates).

    Switch `convoy_via_explicit` (Gilgamesch B.3.2.14 Satz 1) -- it acts
    HERE (pre-conflict), never inside the conflicter:

    - False (default, standard Diplomacy): the [Convoy] flag (via_convoy)
      is purely informational AS LONG AS A LAND ROUTE EXISTS -- a move
      becomes a convoy move exactly when some ordered convoyer convoying
      this movement exists AND forms a route (adjacent or not; this makes
      the convoy swap of two adjacent armies possible, DATC-style: the
      con order claims the move). A FLAGGED move WITHOUT a land route is an
      unambiguous convoy ATTEMPT under both switch positions: it becomes a
      convoy move whose dead route fails in k1 ($criv, full-strength
      stand; DipNet 'no convoy') -- NOT the B.4.2.9 def-0 umove that an
      unflagged impossible move gets.
    - True (Gilgamesch B.3.2.14 scharf): a flagged move is a convoy move
      regardless of any con order (no land fallback; a dead route fails in
      k1's $criv). Unflagged adjacent moves stay land moves even when a
      convoy is ordered (B.3.2.14 Satz 3); unflagged non-adjacent moves
      stay candidates -- the convoy is their only route.

    OrderType.cmve orders (already rewritten by the pre-processor) pass
    through unchanged so the set is idempotent on pre-processed input.
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
        if o.order == OrderType.cmve:
            # already decided by the order pre-processor -- pass through
            cmoves.add(i)
            continue
        if o.order != OrderType.mve or not m.field_exists(o.current) or not o.dest or not m.field_exists(o.dest):
            continue
        if via_explicit and o.via_convoy:
            # B.3.2.14 Satz 1: the explicit flag alone forces the sea route
            # (no land fallback; any unit type -- a dead route fails in k1).
            cmoves.add(i)
            continue
        if o.via_convoy and not can_reach_by_unit(o.current, o.dest, o.utype, m):
            # Flagged move WITHOUT a land route: an unambiguous convoy
            # ATTEMPT under both switch positions -- it becomes a convoy
            # move whose dead route fails in k1 ($criv), i.e. the unit
            # stands at FULL defensive strength (DipNet 'no convoy'; NOT
            # the B.4.2.9 def-0 umove of an unflagged impossible move).
            cmoves.add(i)
            continue
        if (
            o.utype == "A"  # only armies are convoyable (GEO-009)
            and m.superfield_of(o.current) in convoyed_starts
            and convoy_route_exists(m.superfield_of(o.current), m.superfield_of(o.dest), graph)
            and (
                # default: a con order claiming this move makes it a convoy
                # move (swap-capable), adjacent or not. Gilgamesch Satz 3
                # applies only with via_explicit: unflagged adjacent = land.
                not via_explicit or not can_reach_by_unit(o.current, o.dest, o.utype, m)
            )
        ):
            cmoves.add(i)
    return cmoves


def build_convoy_graph(orders: List[Order], m: MapProtocol, via_explicit: bool = False) -> ConvoyGraph:
    convoyers = _convoyer_fields(orders)
    sea_edges, coastal_edges = _convoy_graph_edges(convoyers, m)

    return ConvoyGraph(
        sea_edges=sea_edges,
        coastal_edges=coastal_edges,
        convoyer_fields=convoyers,
        cmove_candidates=classify_cmove_candidates(orders, m, via_explicit=via_explicit),
    )
