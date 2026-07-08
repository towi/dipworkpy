"""Regression: a convoying fleet must only be dislodged by an attack that
actually wins the conflict at its field.

Pinned from DipNet triage (Task 9). The dominant post-geography-wiring FAIL
family (~30 of 41 on the 100-game sample, e.g. yCOKdNHDFvK7BDp8_F1904M,
gIFm7p0bIuoOIz5g_S1902M, EWfQsnYLG5-OZLGU_F1903M) was k1 dislodging a
convoyer against an equal-strength (unsupported) attack that should bounce.
Root cause: k1 resolved the conflict at the attacker's own (uncontested)
field instead of at the convoyer's field, so the attacker's `succeeds` kept
its default True and the convoyer was demoted unconditionally.
"""

from dipworkpy.conflict_game import conflict_game
from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType, Situation, Switches


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current, order=order, dest=dest)


def _run(orders):
    geo = geography_phase(GeographyRequest(orders=orders))
    situation = Situation(orders=geo.orders, switches=Switches())
    cr = conflict_game(
        situation,
        order_geo_info=geo.order_geo_info,
        convoy_graph=geo.convoy_graph,
    )
    return {o.current: o for o in cr.orders}


def test_unsupported_attack_on_convoyer_bounces_convoy_survives():
    """Ge F Den->NTH (str 1) attacks the convoyer En F NTH (def 1): the
    attack bounces, the convoyer is NOT dislodged, and the convoyed move
    Lon->Nor succeeds via the intact route."""
    by = _run(
        [
            mko("En", "A", "Lon", OrderType.mve, "Nor"),  # convoyed army
            mko("En", "F", "NTH", OrderType.con, "Lon"),  # convoyer
            mko("Ge", "F", "Den", OrderType.mve, "NTH"),  # unsupported attacker
        ]
    )
    assert by["NTH"].dislodged is None, by["NTH"]
    assert by["Den"].succeeds is False, by["Den"]
    assert by["Lon"].succeeds is None, by["Lon"]


def test_supported_attack_on_convoyer_still_dislodges():
    """Guard against over-correction: a supported attack (str 2) on the
    convoyer (def 1) still dislodges it and cuts the convoy."""
    by = _run(
        [
            mko("En", "A", "Lon", OrderType.mve, "Nor"),  # convoyed army
            mko("En", "F", "NTH", OrderType.con, "Lon"),  # convoyer
            mko("Ge", "F", "Den", OrderType.mve, "NTH"),  # attacker
            mko("Ge", "F", "SKA", OrderType.msup, "Den"),  # support the attack
        ]
    )
    assert by["NTH"].dislodged is True, by["NTH"]
    assert by["Den"].succeeds is None, by["Den"]
    # convoy route is cut -> the convoyed army is demoted to a hold (it does
    # not reach Nor); the DipNet comparator maps this hld-vs-mve to a fail.
    assert by["Lon"].order == OrderType.hld, by["Lon"]
