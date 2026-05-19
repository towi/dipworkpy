"""Syntax rules SYN-001 .. SYN-008."""
from __future__ import annotations

from typing import Set

from dipworkpy.geo_model import FieldType
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order, OrderType, Switches

VALID_ORDER_TYPES = {OrderType.hld, OrderType.mve, OrderType.hsup, OrderType.msup, OrderType.con}

# Fields where an army can stand: land of any kind (LA, L, LCB, LC, LCA — subfield
# variants LCF are handled via their superfield).
_ARMY_OK_TYPES = {FieldType.LA, FieldType.L, FieldType.LCB, FieldType.LC, FieldType.LCA}
# Fields where a fleet can stand: ocean + any coastal land.
_FLEET_OK_TYPES = {FieldType.O, FieldType.LCB, FieldType.LC, FieldType.LCA, FieldType.LCF}


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


def is_unit_field_mismatch(o: Order, m: MapProtocol, switches: Switches) -> bool:
    """SYN-007: an army on a sea field, or a fleet on a pure inland field.

    Only active when `strict_unit_types=True`. For standard Diplomacy this is
    typically off (the conflict resolver treats both unit types the same), but
    Gilgamesch-style adjudication wants the disambiguation.
    """
    if not switches.strict_unit_types:
        return False
    if not m.field_exists(o.current):
        return False  # SYN-004 will strike it instead
    ftype = m.field_type(o.current)
    if o.utype == "A" and ftype not in _ARMY_OK_TYPES:
        return True
    if o.utype == "F" and ftype not in _FLEET_OK_TYPES:
        return True
    return False
