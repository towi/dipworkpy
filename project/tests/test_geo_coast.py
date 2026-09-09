from dipworkpy.geo_model import MapRef
from dipworkpy.geography.coast import normalize_to_superfield, resolve_coast
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.model import Order, OrderType


def test_normalize_subfield_to_superfield():
    m = resolve_map_ref(MapRef())
    assert normalize_to_superfield("SpN", m) == "Spa"
    assert normalize_to_superfield("Spa", m) == "Spa"
    assert normalize_to_superfield("Vie", m) == "Vie"


def test_resolve_coast_deterministic():
    m = resolve_map_ref(MapRef())
    # F Spa mve LYO — only SpS reaches LYO (SpN's nbrs: Gas, MID, Por; LYO not in them).
    # NB: deviation from plan which used MID (ambiguous: reachable from both coasts).
    o = Order(nation="Fr", utype="F", current="Spa", order=OrderType.mve, dest="LYO")
    coast = resolve_coast(o, m)
    assert coast == "SpS"


def test_resolve_coast_none_for_unambiguous_field():
    m = resolve_map_ref(MapRef())
    # F Bre mve MID — no coast question
    o = Order(nation="Fr", utype="F", current="Bre", order=OrderType.mve, dest="MID")
    coast = resolve_coast(o, m)
    assert coast is None
