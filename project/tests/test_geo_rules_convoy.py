from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.rules import classify_convoy
from dipworkpy.model import Order, OrderType


def _con(current: str, ref: str) -> Order:
    return Order(nation="En", utype="F", current=current, order=OrderType.con, dest=ref)


def test_geo_005_convoyer_not_on_sea():
    m = resolve_map_ref(MapRef())
    # Vie is land, not sea — invalid convoyer
    info = classify_convoy(_con("Vie", "Lon"), m, convoyed_dest="Bel", order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-005"
    assert info.effective_behavior == "holds_supportable"


def test_geo_006_valid_convoyer_nth():
    m = resolve_map_ref(MapRef())
    # F NTH con A Lon mve Bel — NTH is sea, both Lon+Bel adjacent to NTH
    info = classify_convoy(_con("NTH", "Lon"), m, convoyed_dest="Bel", order_index=0)
    assert info.is_valid is True
