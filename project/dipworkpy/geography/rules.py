"""Per-rule order classification (GEO-001 .. GEO-010)."""

from __future__ import annotations

from typing import Optional

from dipworkpy.geo_model import ConvoyGraph, Edge, FieldType, OrderGeoInfo, Passable
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order


def _expanded_fields(fld: str, m: MapProtocol) -> list[str]:
    if not m.field_exists(fld):
        return [fld]
    return [fld, *m.subfields_of(fld)]


def _literal_matches_endpoint(value: str, frm: str, to: str, m: MapProtocol) -> bool:
    if not m.field_exists(value):
        return False
    endpoints = {frm, to}
    endpoint_supers = {m.superfield_of(f) for f in endpoints if m.field_exists(f)}
    return value in endpoints or m.superfield_of(value) in endpoint_supers


def _edge_passable_for_unit(e: Edge, utype: str, frm: str, to: str, m: MapProtocol) -> bool:
    if utype == "A":
        value = e.army
        if value == Passable.YES:
            return True
        if isinstance(value, str) and value not in {p.value for p in Passable}:
            return _literal_matches_endpoint(value, frm, to, m)
        return False

    if utype == "F":
        value = e.fleet
        if value == Passable.YES:
            return True
        if isinstance(value, str) and value not in {p.value for p in Passable}:
            return _literal_matches_endpoint(value, frm, to, m)
        return False

    return False


def _field_can_host_unit(fld: str, utype: str, m: MapProtocol) -> bool:
    if not m.field_exists(fld):
        return False
    ftype = m.field_type(fld)
    if utype == "A":
        if m.superfield_of(fld) != fld:
            return False
        return ftype in {FieldType.L, FieldType.LA, FieldType.LC, FieldType.LCA, FieldType.LCB}
    if utype == "F":
        return ftype in {FieldType.O, FieldType.LC, FieldType.LCA, FieldType.LCB, FieldType.LCF}
    return False


def can_reach_by_unit(
    current: str,
    dest: str,
    utype: str,
    m: MapProtocol,
    *,
    expand_dest: bool = True,
) -> bool:
    """Return whether a unit can move directly, honoring unit, terrain, and coasts."""
    dest_fields = _expanded_fields(dest, m) if expand_dest else [dest]
    for frm in _expanded_fields(current, m):
        if not _field_can_host_unit(frm, utype, m):
            continue
        for to in dest_fields:
            if not _field_can_host_unit(to, utype, m):
                continue
            edge = m.edge(frm, to)
            if edge and _edge_passable_for_unit(edge, utype, frm, to, m):
                return True
    return False


def classify_move(o: Order, m: MapProtocol, order_index: int) -> OrderGeoInfo:
    """Apply GEO-001..003 to a mve order."""
    if o.dest is None or not m.field_exists(o.dest):
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-001",
            invalidity_reason=f"destination {o.dest!r} not on map",
            effective_behavior="holds_no_support",
        )
    if o.dest == o.current:
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-002",
            invalidity_reason="start == destination",
            effective_behavior="holds_no_support",
        )
    # GEO-003: directly reachable by this unit type? Convoy chains are handled
    # later by GEO-009 and may override this classification for cmove orders.
    if not can_reach_by_unit(o.current, o.dest, o.utype, m):
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-003",
            invalidity_reason=(f"{o.utype} {o.current} cannot reach {o.dest} directly (no convoy detected)"),
            effective_behavior="holds_no_support",
        )
    return OrderGeoInfo(
        order_index=order_index,
        is_valid=True,
        effective_behavior="moves",
    )


def classify_convoy(
    o: Order, m: MapProtocol, *, convoyed_dest: str, order_index: int, convoy_graph: ConvoyGraph | None = None
) -> OrderGeoInfo:
    """GEO-005/006 for convoy orders.

    - GEO-005: convoyer must be on a sea field.
    - GEO-006: convoyer must be adjacent to both the army's start (o.dest)
      and the army's destination.
    """
    from dipworkpy.geo_model import FieldType

    if not m.field_exists(o.current):
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-005",
            invalidity_reason=f"convoyer field {o.current!r} unknown",
            effective_behavior="holds_supportable",
        )
    if m.field_type(o.current) != FieldType.O:
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-005",
            invalidity_reason=f"{o.current} is not a sea field",
            effective_behavior="holds_supportable",
        )
    army_start = m.superfield_of(o.dest) if o.dest and m.field_exists(o.dest) else o.dest
    if army_start is None:
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-006",
            invalidity_reason="convoy order does not name an army start field",
            effective_behavior="holds_supportable",
        )
    if convoy_graph is not None:
        from dipworkpy.geography.convoy import convoy_route_uses

        if not convoy_route_uses(
            army_start,
            convoyed_dest,
            o.current,
            convoy_graph,
        ):
            return OrderGeoInfo(
                order_index=order_index,
                is_valid=False,
                invalidity_code="GEO-006",
                invalidity_reason=(f"convoyer {o.current} is not on a route from {army_start} to {convoyed_dest}"),
                effective_behavior="holds_supportable",
            )
    else:
        nbrs = m.neighbors(o.current)
        if army_start not in nbrs or convoyed_dest not in nbrs:
            return OrderGeoInfo(
                order_index=order_index,
                is_valid=False,
                invalidity_code="GEO-006",
                invalidity_reason=(f"convoyer {o.current} not adjacent to both {army_start} and {convoyed_dest}"),
                effective_behavior="holds_supportable",
            )
    return OrderGeoInfo(
        order_index=order_index,
        is_valid=True,
        effective_behavior="moves",
    )


def classify_support(
    o: Order,
    m: MapProtocol,
    *,
    supported_target: str,
    order_index: int,
    move_dest: Optional[str] = None,
    is_msup: bool = False,
) -> OrderGeoInfo:
    """GEO-004. hsup: supporter must reach the held unit's field.
    msup: supporter must reach the supported MOVE's destination
    (move_dest); a msup whose referenced unit has no mve order is void.

    Per Gilgamesch B.3.1.1: no convoy, no furt — strict direct adjacency.
    """
    if not m.field_exists(supported_target):
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=f"supported target {supported_target!r} unknown",
            effective_behavior="holds_supportable",
        )
    if is_msup and move_dest is None:
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=(f"support-to-move for {supported_target!r}, but that unit has no move order"),
            effective_behavior="holds_supportable",
        )
    reach_target = move_dest if is_msup else supported_target
    # The msup+move_dest-is-None case returned above, so reach_target is set.
    assert reach_target is not None
    if not can_reach_by_unit(o.current, reach_target, o.utype, m):
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=(f"{o.utype} {o.current} cannot reach {reach_target} directly"),
            effective_behavior="holds_supportable",
        )
    return OrderGeoInfo(
        order_index=order_index,
        is_valid=True,
        effective_behavior="moves",
    )
