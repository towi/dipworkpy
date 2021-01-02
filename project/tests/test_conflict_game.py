# std lib
import logging
# local
from dipworkpy.model import Situation, Order, OrderType, ConflictResolution, OrderResult, Switches
# under test
from dipworkpy.conflict_game import conflict_game

################################################


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


def mk_oresult(s : str) -> OrderResult:
    """@:param s -- order description to parse, eg "Ge A Vie", "Ge A Vie mve Mun", "Ge A Vie msup Mun".
    Add an "!" and/or an "<" (separated by spaces) to mark the field as "not succeeded" or "disbanded".
    The order type is the short notatation from OrderResult, ie. "msup" instead of "msupport".
    TODO The unit type is currently ignored and set to "?", I do not pass the original info down yet.
    """
    toks = s.split()
    n, u, c, o, d = toks[0:5]
    succeeds = None  if "!" not in toks else False
    dislodged = None  if "<" not in toks else True
    return OrderResult(nation=n, utype='?', current=c, order=o, dest=d, succeeds=succeeds, dislodged=dislodged)


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
        orders = [
            mk_order_h("Ge A Mun hld"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders = [
            mk_oresult("Ge A Mun hld Mun"),
        ],
        pattfields = set()
    )
    assert result == expected


def test_conflict_game_02(verbose=False):
    # arrange
    situation: Situation = Situation(
        orders = [
            mk_order("Au A Vie mve Mun"),
            mk_order_0("Ge A Mun"),
        ],
        switches = Switches(verbose=True)
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders = [
            mk_oresult("Au A Vie mve Mun !"),
            mk_oresult("Ge A Mun hld Mun"),
        ],
        pattfields = set()
    )
    assert result == expected


def test_conflict_game_03():
    # arrange
    situation: Situation = Situation(
        orders = [
            mk_order("En F Lon mve NTH"),
            mk_order("En F CHN msup Lon"),
            mk_order("Ge F NTH con Kie"),
            mk_order("Ge A Kie mve Lon"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders = [
            mk_oresult("En F Lon mve NTH"),
            mk_oresult("En F CHN msup Lon"),
            mk_oresult("Ge F NTH con Kie <"),
            mk_oresult("Ge A Kie mve Lon !"),
        ],
        pattfields = set()
    )
    assert result == expected


def test_conflict_game_02_03():
    # arrange
    situation: Situation = Situation(
        orders = [
            # conflict 02:
            mk_order("Au A Vie mve Mun"),
            mk_order_0("Ge A Mun"),
            # conflict 03:
            mk_order("En F Lon mve NTH"),
            mk_order("En F CHN msup Lon"),
            mk_order("Ge F NTH con Kie"),
            mk_order("Ge A Kie mve Lon"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders = [
            # conflict 02: Vie can not move, Mun holds
            mk_oresult("Au A Vie mve Mun !"),
            mk_oresult("Ge A Mun hld Mun"),
            # conflict 03: Lon moves and breaks convoy, NTH dislodged, Kie fails.
            mk_oresult("En F Lon mve NTH"),
            mk_oresult("En F CHN msup Lon"),
            mk_oresult("Ge F NTH con Kie <"),
            mk_oresult("Ge A Kie mve Lon !"),
        ],
        pattfields = set()
    )
    assert result == expected

################################################


def test_conflict_game_patt_01():
    # arrange
    situation: Situation = Situation(
        orders = [
            mk_order("Ge A Mun mve Vie"),
            mk_order("Au A Tri mve Vie"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders = [
            mk_oresult("Ge A Mun mve Vie !"),
            mk_oresult("Au A Tri mve Vie !"),
        ],
        pattfields = {"Vie"}
    )
    assert result == expected


################################################


if __name__ == "__main__":
    if True:
        logging.basicConfig(level=logging.DEBUG,
                            # format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                            format='%(filename)s:%(lineno)d: [%(levelname)s] %(funcName)s | %(message)s',
                            datefmt='%Y-%m-%d:%H:%M:%S'
                            )
        test_conflict_game_02(verbose=True)
    else:
        import sys
        import pytest
        pytest.main(sys.argv + ['-vv'])
