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
