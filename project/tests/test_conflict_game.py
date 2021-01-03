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
    """
    toks = s.split()
    n, u, c, o, d = toks[0:5]
    succeeds = None  if "!" not in toks else False
    dislodged = None  if "<" not in toks else True
    return OrderResult(nation=n, utype=u, current=c, order=o, dest=d, succeeds=succeeds, dislodged=dislodged)


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
    assert result <= expected # or use == with clear_originals().


def test_conflict_game_02():
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
            mk_oresult("Au A Vie hld Mun !"),  # TODO check if its ok to not change dest field along with order.
            mk_oresult("Ge A Mun hld Mun"),
        ],
        pattfields = set()
    )
    # '<=' ignores 'original'
    assert result <= expected, f"\nres: {result.__log__()} !=\nexp: {expected.__log__()}"
    # better way using '==' but loosing information.
    assert result.clear_originals() == expected, f"\nres: {result.__log__()} !=\nexp: {expected.__log__()}"


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
    assert result <= expected # or use == with clear_originals().


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
    assert result <= expected, f"\nres: {result.__log__()} !=\nexp: {expected.__log__()}" # or use == with clear_originals().

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
            mk_oresult("Ge A Mun hld Vie !"),  # TODO check if changed order but kept dest is ok
            mk_oresult("Au A Tri hld Vie !"),  # TODO check if changed order but kept dest is ok
        ],
        pattfields = {"Vie"}
    )
    assert result <= expected, f"\nres: {result.__log__()}\nexp: {expected.__log__()}" # or use == with clear_originals().
    assert result.clear_originals() == expected  # or use <= to keep information


################################################


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        # format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        format='%(filename)s:%(lineno)d: [%(levelname)s] %(funcName)s | %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S'
                        )
    if False:
        test_conflict_game_patt_01()
    else:
        import sys
        import pytest
        pytest.main(sys.argv + ['-vv'])
