"""Syntax rules SYN-001 .. SYN-008."""
from __future__ import annotations

from typing import Set

from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order, OrderType, Switches

VALID_ORDER_TYPES = {OrderType.hld, OrderType.mve, OrderType.hsup, OrderType.msup, OrderType.con}


def is_unknown_nation(o: Order, known: Set[str]) -> bool:
    return o.nation not in known


def is_unknown_unit_type(o: Order, switches: Switches) -> bool:
    if not switches.strict_unit_types:
        return False
    return o.utype not in {"A", "F"}


def field_exists(o: Order, m: MapProtocol) -> bool:
    return m.field_exists(o.current)


def has_known_order_type(o: Order) -> bool:
    return o.order is None or o.order in VALID_ORDER_TYPES


def has_unit_at_current(o: Order, unit_positions: dict) -> bool:
    return o.current in unit_positions
