"""Per-rule order classification (GEO-001 .. GEO-010)."""
from __future__ import annotations

from dipworkpy.geo_model import OrderGeoInfo
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order


def classify_move(o: Order, m: MapProtocol, order_index: int) -> OrderGeoInfo:
    """Apply GEO-001..003 to a mve order."""
    if o.dest is None or not m.field_exists(o.dest):
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-001",
            invalidity_reason=f"destination {o.dest!r} not on map",
            effective_behavior="holds_no_support",
        )
    if o.dest == o.current:
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-002",
            invalidity_reason="start == destination",
            effective_behavior="holds_no_support",
        )
    # GEO-003: reachable? (direct neighbor — convoy chain check is in later rule)
    if o.dest not in m.neighbors(o.current):
        # not directly adjacent — could still be convoyable (handled by GEO-009)
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-003",
            invalidity_reason=f"{o.dest} not adjacent to {o.current} (no convoy detected)",
            effective_behavior="holds_no_support",
        )
    return OrderGeoInfo(
        order_index=order_index, is_valid=True,
        effective_behavior="moves",
    )


def classify_convoy(o: Order, m: MapProtocol, *, convoyed_dest: str,
                    order_index: int) -> OrderGeoInfo:
    """GEO-005/006 for convoy orders.

    - GEO-005: convoyer must be on a sea field.
    - GEO-006: convoyer must be adjacent to both the army's start (o.dest)
      and the army's destination.
    """
    from dipworkpy.geo_model import FieldType
    if not m.field_exists(o.current):
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-005",
            invalidity_reason=f"convoyer field {o.current!r} unknown",
            effective_behavior="holds_supportable",
        )
    if m.field_type(o.current) != FieldType.O:
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-005",
            invalidity_reason=f"{o.current} is not a sea field",
            effective_behavior="holds_supportable",
        )
    army_start = o.dest  # by DipworkPy convention, con.dest = army start field
    nbrs = m.neighbors(o.current)
    if army_start not in nbrs or convoyed_dest not in nbrs:
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-006",
            invalidity_reason=(
                f"convoyer {o.current} not adjacent to both "
                f"{army_start} and {convoyed_dest}"
            ),
            effective_behavior="holds_supportable",
        )
    return OrderGeoInfo(
        order_index=order_index, is_valid=True,
        effective_behavior="moves",
    )


def classify_support(o: Order, m: MapProtocol, *, supported_target: str,
                     order_index: int) -> OrderGeoInfo:
    """GEO-004: supporter must reach supported_target from a direct neighbor.

    Per Gilgamesch B.3.1.1: no convoy, no furt — strict direct adjacency.
    """
    if not m.field_exists(supported_target):
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=f"supported target {supported_target!r} unknown",
            effective_behavior="holds_supportable",
        )
    if supported_target not in m.neighbors(o.current):
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=f"{o.current} cannot reach {supported_target} directly",
            effective_behavior="holds_supportable",
        )
    return OrderGeoInfo(
        order_index=order_index, is_valid=True,
        effective_behavior="moves",
    )
