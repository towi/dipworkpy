from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.rules import classify_support
from dipworkpy.model import Order, OrderType


def _sup(current: str, dest: str, order=OrderType.hsup) -> Order:
    return Order(nation="Au", utype="A", current=current, order=order, dest=dest)


def test_valid_hold_support_direct_neighbor():
    m = resolve_map_ref(MapRef())
    # Boh supports Vie (direct neighbor)
    info = classify_support(_sup("Boh", "Vie"), m, supported_target="Vie", order_index=0)
    assert info.is_valid is True
    assert info.effective_behavior == "moves"


def test_invalid_support_unreachable():
    m = resolve_map_ref(MapRef())
    # Vie tries to support a unit in Lon — Lon is not adjacent to Vie
    info = classify_support(_sup("Vie", "Lon"), m, supported_target="Lon", order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-004"
    assert info.effective_behavior == "holds_supportable"
