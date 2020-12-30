from dipworkpy.model import Situation, Order, OrderType
# under test
from dipworkpy.conflict_game import conflict_game


def mk_order(spec: str) -> Order:
    nation, utype, current, ordertype, dest = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=ordertype, dest=dest)


def mk_order_h(spec: str) -> Order:
    """parse order missing dest field. Probably not very useful, because it must be a hold order to be valid."""
    nation, utype, current, ordertype = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=ordertype, dest=None)


def mk_order_0(spec: str) -> Order:
    """parse order missing ordertype and dest field"""
    nation, utype, current = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=None, dest=None)

################################################


def test_mk_order():
    o = mk_order_0("En A Vie")
    e = Order(nation="En", utype="A", current="Vie", order=None, dest=None)
    assert o == e
    assert mk_order_h("En A Vie hld") == Order(nation="En", utype="A", current="Vie", order=OrderType.hld, dest=None)
    assert mk_order_h("En A Vie hld") == Order(nation="En", utype="A", current="Vie", order=OrderType.hld, dest=None)
    assert mk_order("En A Vie mve Mun") == Order(nation="En", utype="A", current="Vie", order=OrderType.mve, dest="Mun")
    assert mk_order("En A Vie hsup Mun") == Order(nation="En", utype="A", current="Vie", order=OrderType.hsup, dest="Mun")
    assert mk_order("En A Vie msup Mun") == Order(nation="En", utype="A", current="Vie", order=OrderType.msup, dest="Mun")

################################################


def test_conflict_game_01():
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order_h("Ge A Mun hld"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    assert result


def test_conflict_game_02():
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("Au A Vie mve Mun"),
            mk_order_0("Ge A Mun"),
            mk_order("En F Lon mve NTH"),
            mk_order("En F CHN msup Lon"),
            mk_order("Ge F NTH con Kie"),
            mk_order("Ge A Kie mve Lon"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    assert result


if __name__ == "__main__":
    import sys
    import pytest

    pytest.main(sys.argv)
