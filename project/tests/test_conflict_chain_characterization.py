"""Characterization: rule behaviors behind the two ex-DipNet-FAIL cases.

Both scenarios adjudicate correctly on the bare engine; the dataset
failures came from the evaluator's (removed) void->hld rewrite.
"""

from dipworkpy.conflict_game import conflict_game
from dipworkpy.model import Order, OrderType, Situation


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current, order=order, dest=dest)


def _by_current(orders):
    cr = conflict_game(Situation(orders=orders))
    return {o.current: o for o in cr.orders}


def test_supported_attack_beats_weak_attack_into_vacated_field():
    """Tyr->Tri (str 3) vs Bud->Tri (str 1) while Tri->Ser leaves:
    Tyr enters, Bud bounces, the vacating unit is not dislodged."""
    by = _by_current(
        [
            mko("It", "A", "Tri", OrderType.mve, "Ser"),
            mko("It", "A", "Tyr", OrderType.mve, "Tri"),
            mko("It", "A", "Ven", OrderType.msup, "Tyr"),
            mko("It", "F", "ADR", OrderType.msup, "Tyr"),
            mko("Ru", "A", "Bud", OrderType.mve, "Tri"),
        ]
    )
    assert by["Tri"].succeeds is None and by["Tri"].dislodged is None, by["Tri"]
    assert by["Tyr"].succeeds is None, by["Tyr"]
    assert by["Bud"].succeeds is False, by["Bud"]


def test_no_self_dislodgement_in_bounce_chain():
    """Fr Ber->Mun (str 3) vs Au Tyr->Mun (str 2) while Fr Mun->Sil
    bounces: France may not dislodge its own unit; its strength still
    bounces Tyr; the chain behind Tyr bounces too."""
    by = _by_current(
        [
            mko("Au", "A", "Pie", OrderType.mve, "Tyr"),
            mko("Au", "A", "Tus", OrderType.mve, "Pie"),
            mko("Au", "A", "Tyr", OrderType.mve, "Mun"),
            mko("Au", "A", "Boh", OrderType.msup, "Tyr"),
            mko("Au", "A", "Pru", OrderType.mve, "Ber"),
            mko("Au", "A", "Sil", OrderType.msup, "Pru"),
            mko("Fr", "A", "Ber", OrderType.mve, "Mun"),
            mko("Fr", "A", "Mun", OrderType.mve, "Sil"),
            mko("Fr", "A", "Kie", OrderType.msup, "Ber"),
            mko("Fr", "A", "Ruh", OrderType.msup, "Ber"),
        ]
    )
    assert by["Mun"].dislodged is None, by["Mun"]
    for f in ("Pie", "Tus", "Tyr", "Ber", "Mun", "Pru"):
        assert by[f].succeeds is False, (f, by[f])


def test_no_self_dislodgement_when_head_to_head_loser_returns():
    """Head-to-head Fr Kie<->Au Ber, plus a same-nation secondary attacker
    Fr HEL->Kie (supported by Ruh, str 2). Fr Kie->Ber bounces against
    Au Pru->Ber (both str 2) and returns to Kie; France may not then
    dislodge its own returning A Kie with F HEL.

    Pinned from DipNet triage (Task 9): 5M65XaqXlieNDQVV_S1907M,
    h9QEPT6s5-Fi1WrV_F1910M, kLq1Qi6MqjKKDd4G_F1917M. In the dataset the
    supporting order is even flagged `void` (supporting the dislodgement of
    an own unit). Root cause: the head-to-head loser kept fcategory=3, so k4
    never re-resolved its field once it bounced back, and the self-dislodge
    guard (which needs defensive_strength>0) never ran for the third
    attacker whose win was computed while the field was still vacating."""
    by = _by_current(
        [
            mko("Fr", "A", "Kie", OrderType.mve, "Ber"),
            mko("Fr", "F", "BAS", OrderType.msup, "Kie"),
            mko("Au", "A", "Ber", OrderType.mve, "Kie"),  # head-to-head vs Kie
            mko("Au", "A", "Pru", OrderType.mve, "Ber"),
            mko("Au", "A", "Sil", OrderType.msup, "Pru"),
            mko("Fr", "F", "HEL", OrderType.mve, "Kie"),  # same-nation attacker
            mko("Fr", "A", "Ruh", OrderType.msup, "HEL"),
        ]
    )
    assert by["Kie"].dislodged is None, by["Kie"]
    assert by["HEL"].succeeds is False, by["HEL"]
    # Kie's own move still fails (bounced at Ber); it stays put.
    assert by["Kie"].succeeds is False, by["Kie"]
