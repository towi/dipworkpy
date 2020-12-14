from dipworkpy.model import Situation, Order
# under test
from dipworkpy.conflict_game import conflict_game


def mk_order(spec: str) -> Order:
    nation, utype, current, ordertype, target = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=ordertype, target=target)


def mk_order_brief(spec: str) -> Order:
    nation, utype, current, ordertype = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=ordertype, target=None)


def mk_order_none(spec: str) -> Order:
    nation, utype, current = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=None, target=None)


def test_conflict_game_01():
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order_brief("Ge A Mun hld"),
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
            mk_order_none("Ge A Mun"),
            mk_order("En F Lon mve NTH"),
            mk_order("En F CHN sup Lon"),
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
