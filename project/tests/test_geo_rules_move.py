from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.rules import classify_move
from dipworkpy.model import Order, OrderType


def _o(current: str, dest: str) -> Order:
    return Order(nation="Au", utype="A", current=current,
                 order=OrderType.mve, dest=dest)


def test_geo_001_unknown_destination():
    m = resolve_map_ref(MapRef())
    info = classify_move(_o("Vie", "ZZZ"), m, order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-001"
    assert info.effective_behavior == "holds_no_support"


def test_geo_002_start_equals_destination():
    m = resolve_map_ref(MapRef())
    info = classify_move(_o("Vie", "Vie"), m, order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-002"
    assert info.effective_behavior == "holds_no_support"


def test_geo_003_not_reachable():
    m = resolve_map_ref(MapRef())
    info = classify_move(_o("Vie", "Lon"), m, order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-003"
    assert info.effective_behavior == "holds_no_support"


def test_valid_move_is_moves():
    m = resolve_map_ref(MapRef())
    info = classify_move(_o("Vie", "Boh"), m, order_index=0)
    assert info.is_valid is True
    assert info.effective_behavior == "moves"
