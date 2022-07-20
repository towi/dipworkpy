"""
test cases from
http://web.inter.nl.net/users/L.B.Kruijswijk/
"""

# std lib
import sys
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


def mk_oresult(s: str) -> OrderResult:
    """@:param s -- order description to parse, eg "Ge A Vie", "Ge A Vie mve Mun", "Ge A Vie msup Mun".
    Add an "!" and/or an ">" (separated by spaces) to mark the field as "not succeeded" or "dislodged".
    The order type is the short notation from OrderResult, ie. "msup" instead of "msupport".
    """
    toks = s.split()
    n, u, c, o, d = toks[0:5]
    succeeds = None  if "!" not in toks else False
    dislodged = None  if ">" not in toks else True
    return OrderResult(nation=n, utype=u, current=c, order=o, dest=d, succeeds=succeeds, dislodged=dislodged)

################################################


def test_6_a_1():
    """
    === 6.A.1 TEST CASE, MOVING TO AN AREA THAT IS NOT A NEIGHBOUR ===

    Check if an illegal move (without convoy) will fail.

        England:
        F North Sea - Picardy

    Order should fail.
    """
    pass  # requires geography

"""
...
many more skipped tests
...
"""


def test_6_a_11():
    """
    === 6.A.11. TEST CASE, SIMPLE BOUNCE ===

    Two armies bouncing on each other.

        Austria:
        A Vienna - Tyrolia

        Italy:
        A Venice - Tyrolia

    The two units bounce.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("Au A Vie mve Tyr"),
            mk_order("It A Ven mve Tyr"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("Au A Vie mve Tyr !"),  # TODO check if its ok to not change dest field along with order.
            mk_oresult("It A Ven mve Tyr !"),  # TODO check if its ok to not change dest field along with order.
        ],
        pattfields={"Tyr"}
    )
    result.show(sys.stderr, line_prefix="| ")
    # '<=' ignores 'original'
    assert result <= expected, f"\nres: {result.__log__()} !=\nexp: {expected.__log__()}"


################################################


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        # format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        format='%(filename)s:%(lineno)d: [%(levelname)s] %(funcName)s | %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S'
                        )
    if True:
        test_6_a_11()
    else:
        import pytest
        pytest.main(sys.argv + ['-vv'])
