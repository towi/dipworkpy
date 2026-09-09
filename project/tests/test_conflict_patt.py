"""Patt marking: genuine movement-phase standoffs (C.2.2 / C.2.3.1) on t_field.patt.

Gilgamesch semantics:
- C.2.2 (simultaneous attack): several equally-strong strongest ATTACKERS on
  one field -> Patt; no attacker enters, an occupant is besieged, not
  dislodged (belagerte Garnison). The defender's strength does not take part
  in this comparison: a SINGLE strongest attacker is evaluated as a simple
  attack (C.2.1), where a tie with the defender is a plain bounce.
- C.2.3.1 (head-to-head): equal strengths in the first (border) comparison ->
  Patt, both units stand.
- Purpose: C.3.1.3.2 forbids retreats into fields where a movement-phase Patt
  took place; the writer consumes the flag (Task 10).

Semantics note -- why the flag is MONOTONE (never reset per call):
resolve_conflict_at_field is called multiple times per field. Probed on the
engine (Mun/Tri->Vie): the k4 chain loop first resolves Vie with both
attackers (tie -> Patt), then umove-s the bounced attackers ($chain4) and
re-resolves the SAME field in the next iteration with ZERO attackers. The
same happens to head-to-head fields (both become umove, and k4 re-marks
umove destination fields, so they ARE re-resolved). A per-call reset would
therefore erase exactly the canonical C.2.2/C.2.3.1 Patt cases. Conversely,
no resolution can invalidate a marked tie: within a phase strengths are
fixed, attackers only ever leave the active set by failing their (single)
move -- i.e. at this very field -- and a tie broken in a later phase always
ends with the winner occupying the field, which makes the flag moot for the
C.3.1.3.2 check anyway (C.3.1.3.1 requires an empty retreat field). k2-marked
fields (supporter fields: order msup, fcategory 2) are never re-resolved at
all: k4 only re-marks fcategory-0/umove-order destinations. Hence "a k2 Patt
becoming obsolete through k4 re-resolution" is not constructible, and the
pinned invariant below is instead: a marked Patt survives every
re-resolution (tests: two_equal_attackers..., head_to_head_tie_survives...).
"""

from dipworkpy.conflict_game import parser
from dipworkpy.eval.eval_model import t_order
from dipworkpy.model import Order, OrderType, Situation
import dipworkpy.eval as dip_eval_mod


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current, order=order, dest=dest)


def run_world(orders):
    """Adjudicate like conflict_game() but keep the t_world for introspection."""
    world = parser(Situation(orders=orders))
    dip_eval_mod.k1_evaluation(world)
    dip_eval_mod.k2_evaluation(world)
    dip_eval_mod.k3_evaluation(world)
    dip_eval_mod.k4_evaluation(world)
    dip_eval_mod.k0_evaluation(world)
    return world


def test_single_attacker_bounce_is_no_patt():
    """C.2.1: one attacker vs an equal holder is a plain bounce, not a Patt."""
    world = run_world(
        [
            mko("Au", "A", "Mun", OrderType.mve, "Ber"),
            mko("Ge", "A", "Ber", OrderType.hld),
        ]
    )
    assert world.get_field("Mun").order == t_order.umove  # genuine bounce
    assert world.get_field("Ber").patt is False


def test_strongest_attacker_tying_defender_is_no_patt():
    """C.2.1 vs C.2.2 boundary: with two attackers, the single strongest (Mun,
    str 2) ties the defender (Ber, defval 2) -> all bounce, but per C.2.2 the
    single strongest attacker is evaluated as a simple attack: no Patt.
    (draw_a alone would misclassify this: it conflates attacker ties with
    defender ties.)"""
    world = run_world(
        [
            mko("Ge", "A", "Ber", OrderType.hld),
            mko("Ge", "A", "Kie", OrderType.hsup, "Ber"),  # Ber defval 2
            mko("Au", "A", "Mun", OrderType.mve, "Ber"),
            mko("Au", "A", "Sil", OrderType.msup, "Mun"),  # Mun str 2
            mko("Ru", "A", "Pru", OrderType.mve, "Ber"),  # str 1
        ]
    )
    assert world.get_field("Mun").order == t_order.umove  # 2 vs 2 bounce
    assert world.get_field("Pru").order == t_order.umove
    assert world.get_field("Ber").patt is False


def test_two_equal_attackers_on_empty_field_patt():
    """C.2.2 (patt_01 topology): two equally strong attackers on an empty
    field -> Patt. Vie is resolved twice (the k4 chain loop re-resolves it
    with zero attackers after the bounce); the flag must survive that."""
    world = run_world(
        [
            mko("Au", "A", "Mun", OrderType.mve, "Vie"),
            mko("It", "A", "Tri", OrderType.mve, "Vie"),
        ]
    )
    assert world.get_field("Mun").order == t_order.umove
    assert world.get_field("Tri").order == t_order.umove
    vie = world.get_field("Vie")
    assert vie._events.count("$C") == 2  # re-resolved in the k4 chain loop
    assert vie.patt is True


def test_beleaguered_garrison_patt():
    """C.2.2: three equally strong attackers + holder -> Patt; the garrison
    is besieged, not dislodged (6.F.1-style Mun/Pru/War->Ber + Ber hld)."""
    world = run_world(
        [
            mko("Au", "A", "Mun", OrderType.mve, "Ber"),
            mko("Ru", "A", "Pru", OrderType.mve, "Ber"),
            mko("Ru", "A", "War", OrderType.mve, "Ber"),
            mko("Ge", "A", "Ber", OrderType.hld),
        ]
    )
    assert world.get_field("Mun").order == t_order.umove
    assert world.get_field("Ber").succeeds is True  # garrison stands
    assert world.get_field("Ber").patt is True


def test_equal_attackers_below_holder_strength_still_patt():
    """C.2.2 letter: the Patt comparison runs among the attackers only
    ("fuer jede dieser Einheiten"); two equally strong strongest attackers
    are a Patt even when the holder out-strengths them. (draw_a alone would
    miss this tie: maxstrength_a starts at the defender's defval.)"""
    world = run_world(
        [
            mko("Ge", "A", "Ber", OrderType.hld),
            mko("Ge", "A", "Kie", OrderType.hsup, "Ber"),  # defval 2
            mko("Au", "A", "Mun", OrderType.mve, "Ber"),  # str 1
            mko("Ru", "A", "Pru", OrderType.mve, "Ber"),  # str 1
        ]
    )
    assert world.get_field("Mun").order == t_order.umove
    assert world.get_field("Pru").order == t_order.umove
    assert world.get_field("Ber").patt is True


def test_head_to_head_tie_marks_both_fields():
    """C.2.3.1: equal strengths in the first comparison -> Patt; both units
    stand, BOTH fields are marked."""
    world = run_world(
        [
            mko("Fr", "A", "Kie", OrderType.mve, "Ber"),
            mko("Au", "A", "Ber", OrderType.mve, "Kie"),
        ]
    )
    assert world.get_field("Kie").order == t_order.umove
    assert world.get_field("Ber").order == t_order.umove
    assert world.get_field("Kie").patt is True
    assert world.get_field("Ber").patt is True


def test_head_to_head_tie_patt_survives_k4():
    """The k3-marked head-to-head Patt survives the k4 re-resolution: both
    bounced units become umove and k4 re-marks umove destination fields, so
    Kie/Ber ARE re-resolved (with zero active attackers) -- the C.2.3.1 Patt
    must not be recomputed away. A third attacker joins the standoff at Kie."""
    world = run_world(
        [
            mko("Fr", "A", "Kie", OrderType.mve, "Ber"),
            mko("Au", "A", "Ber", OrderType.mve, "Kie"),
            mko("Ru", "A", "Mun", OrderType.mve, "Kie"),
        ]
    )
    assert world.get_field("Mun").order == t_order.umove  # bounced at Kie
    assert world.get_field("Kie").patt is True
    assert world.get_field("Ber").patt is True


def test_head_to_head_with_winner_no_patt():
    """C.2.3.1 with a winner (one side supported): no Patt anywhere; the
    winner dislodges the loser."""
    world = run_world(
        [
            mko("Fr", "A", "Kie", OrderType.mve, "Ber"),
            mko("Fr", "A", "Ruh", OrderType.msup, "Kie"),  # Kie str 2
            mko("Au", "A", "Ber", OrderType.mve, "Kie"),
        ]
    )
    assert world.get_field("Kie").succeeds is True
    assert world.get_field("Kie").patt is False
    assert world.get_field("Ber").patt is False


def test_single_strongest_of_three_attackers_no_patt():
    """C.2.2: three attackers, one strongest -> no Patt; the winner moves in."""
    world = run_world(
        [
            mko("Au", "A", "Mun", OrderType.mve, "Ber"),
            mko("Au", "A", "Sil", OrderType.msup, "Mun"),  # Mun str 2
            mko("Ru", "A", "Pru", OrderType.mve, "Ber"),
            mko("Ru", "A", "War", OrderType.mve, "Ber"),
        ]
    )
    assert world.get_field("Mun").succeeds is True  # winner moves in
    assert world.get_field("Pru").order == t_order.umove
    assert world.get_field("Ber").patt is False


def test_k2_standoff_on_supporter_field_patt():
    """k2-time Patt: the supporter Kie (msup Mun->Ber) is attacked by two
    equally strong units (the counterattacking Ber and Sil) -> C.2.2 standoff
    in the k2 critical conflict. k2 fields (supporter fields, order msup,
    fcategory 2) are never re-resolved by k4 (it only re-marks
    fcategory-0/umove destinations), so the k2 marking is final."""
    world = run_world(
        [
            mko("Au", "A", "Mun", OrderType.mve, "Ber"),
            mko("Au", "A", "Kie", OrderType.msup, "Mun"),  # supporter
            mko("Ge", "A", "Ber", OrderType.mve, "Kie"),  # counterattack
            mko("Ru", "A", "Sil", OrderType.mve, "Kie"),  # 2nd equal attacker
        ]
    )
    assert world.get_field("Ber").order != t_order.nmove  # bounced/annulled
    assert world.get_field("Sil").order == t_order.umove
    assert world.get_field("Kie").patt is True
