"""GEO-004: support-to-move must validate against the move's destination."""

from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current, order=order, dest=dest)


def _geo_for(orders, current):
    geo = geography_phase(GeographyRequest(orders=orders))
    idx = next(i for i, o in enumerate(geo.orders) if o.current == current)
    return geo.order_geo_info[idx]


def test_msup_valid_when_supporter_reaches_move_dest():
    # Mun<->Sil adjacent, Mun<->War NOT adjacent: support is legal.
    orders = [
        mko("Ru", "A", "War", OrderType.mve, "Sil"),
        mko("Ge", "A", "Mun", OrderType.msup, "War"),
    ]
    info = _geo_for(orders, "Mun")
    assert info.is_valid, info


def test_msup_invalid_when_supporter_cannot_reach_move_dest():
    # Supported move goes to War; Mun cannot reach War.
    orders = [
        mko("Ru", "A", "Sil", OrderType.mve, "War"),
        mko("Ge", "A", "Mun", OrderType.msup, "Sil"),
    ]
    info = _geo_for(orders, "Mun")
    assert not info.is_valid, info
    assert info.invalidity_code == "GEO-004", info
    assert info.effective_behavior == "holds_supportable", info


def test_msup_without_companion_move_is_invalid():
    # Referenced unit holds -> support-to-move is void.
    orders = [
        mko("Ru", "A", "Sil", OrderType.hld),
        mko("Ge", "A", "Mun", OrderType.msup, "Sil"),
    ]
    info = _geo_for(orders, "Mun")
    assert not info.is_valid, info
    assert info.invalidity_code == "GEO-004", info


def test_hsup_unchanged_checks_held_units_field():
    orders = [
        mko("En", "F", "Lon", OrderType.hld),
        mko("En", "F", "NTH", OrderType.hsup, "Lon"),
    ]
    info = _geo_for(orders, "NTH")
    assert info.is_valid, info
