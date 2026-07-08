"""B.4.2.9 vs B.4.2.10 - invalid mve vs invalid hld/sup/con."""

from dipworkpy.conflict_game import conflict_game
from dipworkpy.geo_model import OrderGeoInfo
from dipworkpy.model import Order, OrderType, Situation


def test_invalid_mve_not_hold_supportable():
    """Per B.4.2.9: A unit with an invalid mve does NOT receive hold-support."""
    situation = Situation(
        orders=[
            Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="ZZZ"),
            Order(nation="Au", utype="A", current="Bud", order=OrderType.hsup, dest="Vie"),
            Order(nation="Ge", utype="A", current="Boh", order=OrderType.mve, dest="Vie"),
        ]
    )
    geo = [
        OrderGeoInfo(order_index=0, is_valid=False, invalidity_code="GEO-001", effective_behavior="holds_no_support"),
        OrderGeoInfo(order_index=1, is_valid=True, effective_behavior="moves"),
        OrderGeoInfo(order_index=2, is_valid=True, effective_behavior="moves"),
    ]
    result = conflict_game(situation, order_geo_info=geo)
    # Vie should be dislodged: hsup from Bud doesn't apply (Vie was "moving")
    vie_result = next(r for r in result.orders if r.current == "Vie")
    assert vie_result.dislodged is True


def test_invalid_sup_holds_and_is_supportable():
    """Per B.4.2.10: A unit with an invalid sup holds and IS hold-supportable."""
    situation = Situation(
        orders=[
            Order(nation="Au", utype="A", current="Vie", order=OrderType.hsup, dest="ZZZ"),
            Order(nation="Au", utype="A", current="Bud", order=OrderType.hsup, dest="Vie"),
            Order(nation="Ge", utype="A", current="Boh", order=OrderType.mve, dest="Vie"),
        ]
    )
    geo = [
        OrderGeoInfo(order_index=0, is_valid=False, invalidity_code="GEO-004", effective_behavior="holds_supportable"),
        OrderGeoInfo(order_index=1, is_valid=True, effective_behavior="moves"),
        OrderGeoInfo(order_index=2, is_valid=True, effective_behavior="moves"),
    ]
    result = conflict_game(situation, order_geo_info=geo)
    # Vie should NOT be dislodged: Bud's hsup helps Vie hold against Boh
    vie_result = next(r for r in result.orders if r.current == "Vie")
    assert vie_result.dislodged is not True
