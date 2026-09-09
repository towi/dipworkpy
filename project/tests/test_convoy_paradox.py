"""
DATC 6.F.13 - 6.F.24: the convoy paradox family, per Gilgamesch B.3.2.15
(convoy cut immunity) + B.3.2.15 footnote 6 (ambiguity fallback).

Two structural rules replace an unbounded fixpoint:

(a) B.3.2.15 cut immunity (resolves 6.F.13-6.F.21): a convoyed army does
    NOT cut the support of a unit located at its convoy's destination
    field when that support is used FOR AN ATTACK ON (msup only, literal
    text: "Unterstützung ... für einen Angriff") a fleet that is
    NECESSARY for the convoy. Necessary = present on every surviving
    route (the route check without that fleet fails). A HOLD-support of a
    necessary convoyer is "fürs Halten", not "für einen Angriff" -> it
    stays cuttable (6.F.18 resolves via fn6 instead). Multi-route cases
    (6.F.13/19/20): the fleet is not necessary -> the cut is allowed.

(b) Footnote 6 ambiguity fallback (resolves 6.F.22-6.F.24): remaining
    circular cases are cross-convoy cut dependencies. k1 evaluates the
    convoy layer under two extreme cut regimes -- optimistic (all
    B.3.2.15-permitted cmove cuts applied) and pessimistic (no cmove
    cuts at all). A cmove whose convoy-route status DIVERGES between the
    regimes is ambiguous: it stands and its cuts are void ("bleiben alle
    beteiligten Einheiten stehen"). Exactly 3 passes, deterministic.

Each test asserts the GILGAMESCH outcome. B.3.2.15 restricts the cut
immunity to NECESSARY convoyers of the cutter's OWN convoy -- the
modern (2000/2023EE) rule family, NOT the literal 1982 rule (which
immunised any support targeting a body of water containing a convoying
fleet, cf. DATC issue 4.A.2). Consequences re-derived from the rule
text: 6.F.19/6.F.20 cut (fleet not necessary), 6.F.21 -- where the cut
of the Clyde support is made by NORWAY, itself a convoyed move whose
own convoy (via Nws) does not involve NAO -- is NOT protected and so
yields DATC's preferred outcome (see the NEEDS_CONTEXT note in
test_6_f_21_dads_army).

Note on 6.F.18 (betrayal): under the LITERAL B.3.2.15 the hold-support
of the necessary North Sea convoyer is NOT protected (hold-support is
"fürs Halten", not "für einen Angriff"), so London's cut of it is legal
-- but the cut is self-defeating (cut -> Nth dislodged 2v1 -> route
dead -> cut void): a circularity with no consistent resolution, resolved
by the footnote-6 fallback (divergent route status between the cut
regimes -> ambiguous -> the army stands, its cuts void, the 2v2 defense
holds, nobody is dislodged).

The tests run on the legacy engine (conflict_game without a convoy
graph, routing engine "always"): a route is alive iff at least one
ORDERED convoyer was not dislodged, which models exactly the topologies
of these cases (fleet f is necessary iff no other ordered convoyer
remains). All field names are standard-map names; the legacy path does
not evaluate land adjacency, so no topology adaptation was needed.
"""

# std lib
import sys
import logging

# 3rd party
import pytest

# local
from dipworkpy.model import Situation, Order, ConflictResolution, OrderResult, Switches
from dipworkpy.eval.eval_model import t_field, t_order
import dipworkpy.eval as dip_eval_mod

# under test
from dipworkpy.conflict_game import conflict_game, parser as conflict_game_parser


################################################


def mk_order(spec: str) -> Order:
    nation, utype, current, ordertype, dest = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=ordertype, dest=dest)


def mk_order_via(spec: str) -> Order:
    """mk_order with via_convoy=True (GEO-010 "mve [Convoy]")."""
    return mk_order(spec).model_copy(update={"via_convoy": True})


def mk_oresult(s: str) -> OrderResult:
    """@:param s -- order description to parse, eg "Ge A Vie", "Ge A Vie mve Mun", "Ge A Vie msup Mun".
    Add an "!" and/or an ">" (separated by spaces) to mark the field as "not succeeded" or "dislodged".
    The order type is the short notation from OrderResult, ie. "msup" instead of "msupport".
    """
    toks = s.split()
    n, u, c, o, d = toks[0:5]
    succeeds = None if "!" not in toks else False
    dislodged = None if ">" not in toks else True
    return OrderResult(nation=n, utype=u, current=c, order=o, dest=d, succeeds=succeeds, dislodged=dislodged)


def assert_resolution(situation: Situation, expected_orders, expected_pattfields):
    """Strict full-resolution assertion.

    NB: deliberately NOT the `result <= expected` convention of
    test_conflict_datc.py -- list `<=` short-circuits on the first order
    whose lenient OrderResult.__le__ (which skips `original`) succeeds,
    so differences in LATER orders (exactly the markers these paradox
    cases hinge on) would pass silently. clear_originals() + `==` is the
    strict comparison the model docstring itself recommends.
    """
    result = conflict_game(situation)
    result.clear_originals()
    expected = ConflictResolution(orders=[mk_oresult(o) for o in expected_orders], pattfields=expected_pattfields)
    expected.clear_originals()
    assert result == expected, f"\nres: {result.__log__()}\n!=\nexp: {expected.__log__()}"
    return result


def test_6_f_13_unwanted_alternative():
    """6.F.13: England orders TWO routes for Lon->Bel; the North Sea fleet
    is dislodged, but the unwanted alternative (ENG) survives, so the army
    moves. The dislodged fleet's route is irrelevant."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("En A Lon mve Bel"),
                mk_order("En F NTH con Lon"),
                mk_order("Fr F ENG con Lon"),
                mk_order("Ge F Hol msup Den"),
                mk_order("Ge F Den mve NTH"),
            ]
        ),
        [
            "En A Lon mve Bel",  # succeeds via the surviving ENG route
            "En F NTH hld Lon >",  # dislodged -> disrupted (post-$cdsl convoyer reports hld)
            "Fr F ENG con Lon",  # available: the convoy ran
            "Ge F Hol msup Den",  # given
            "Ge F Den mve NTH",  # succeeds
        ],
        set(),
    )


def test_6_f_14_simple_paradox():
    """6.F.14: Bre->Lon is convoyed by the ENG fleet that Wal (supported by
    Lon) dislodges. B.3.2.15: Lon sits at the convoy's destination and its
    support attacks the NECESSARY convoyer -> not cut. The route dies, so
    Bre stands and cuts nothing (DATC 6.F.6: a disrupted convoy does not
    cut support)."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("En F Lon msup Wal"),
                mk_order("En F Wal mve ENG"),
                mk_order("Fr A Bre mve Lon"),
                mk_order("Fr F ENG con Bre"),
            ]
        ),
        [
            "En F Lon msup Wal",  # given: B.3.2.15-protected, not cut
            "En F Wal mve ENG",  # succeeds 2v1
            "Fr A Bre hld Lon",  # route dead -> stands, no cut
            "Fr F ENG hld Bre >",  # dislodged -> disrupted
        ],
        set(),
    )


def test_6_f_16_pandins_paradox():
    """6.F.16 Pandin: the attacked unit (Lon) protects the convoyer via a
    beleaguered garrison. Lon's support is B.3.2.15-protected -> Wal and
    Bel bounce 2v2 at ENG, the convoy survives, but Bre bounces 1v1 at
    Lon."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("En F Lon msup Wal"),
                mk_order("En F Wal mve ENG"),
                mk_order("Fr A Bre mve Lon"),
                mk_order("Fr F ENG con Bre"),
                mk_order("Ge F Nth msup Bel"),
                mk_order("Ge F Bel mve ENG"),
            ]
        ),
        [
            "En F Lon msup Wal",  # given: protected
            "En F Wal hld ENG !",  # 2v2 tie -> bounces
            "Fr A Bre hld Lon !",  # convoy alive, but bounces 1v1 at Lon
            "Fr F ENG con Bre",  # convoy ran (army bounced at dest)
            "Ge F Nth msup Bel",  # given
            "Ge F Bel hld ENG !",  # 2v2 tie -> bounces
        ],
        {"ENG"},
    )


def test_6_f_17_pandins_extended_paradox():
    """6.F.17: as 6.F.16, but France supports Bre->Lon from Yorkshire. The
    garrison still holds ENG (2v2 tie), Lon's support is protected, and
    the supported Bre dislodges Lon."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("En F Lon msup Wal"),
                mk_order("En F Wal mve ENG"),
                mk_order("Fr A Bre mve Lon"),
                mk_order("Fr F ENG con Bre"),
                mk_order("Fr F Yor msup Bre"),
                mk_order("Ge F Nth msup Bel"),
                mk_order("Ge F Bel mve ENG"),
            ]
        ),
        [
            "En F Lon msup Wal >",  # protected, but dislodged by Bre
            "En F Wal hld ENG !",  # 2v2 tie -> bounces
            "Fr A Bre mve Lon",  # succeeds 2v1 (Yor support, Lon's cut void)
            "Fr F ENG con Bre",  # convoy ran
            "Fr F Yor msup Bre",  # given
            "Ge F Nth msup Bel",  # given
            "Ge F Bel hld ENG !",  # 2v2 tie -> bounces
        ],
        {"ENG"},
    )


def test_6_f_18_betrayal_paradox():
    """6.F.18 betrayal, literal B.3.2.15 + fn6 fallback: France
    hold-supports the North Sea convoyer of the English army attacking
    France's own supporter in Belgium. A hold-support is "fürs Halten",
    not "für einen Angriff" -> NOT B.3.2.15-protected -> London's cut of
    it is legal. But the cut is self-defeating (cut -> Nth's defense drops
    to 1 -> Skagerrak dislodges Nth 2v1 -> London's route dies -> the cut
    is void): no consistent resolution. Route status diverges between the
    cut regimes (optimistic: dead; pessimistic: the 2v2 holds, alive) ->
    footnote 6: London stands, its cuts are void, the 2v2 defense holds,
    nobody is dislodged."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("En F Nth con Lon"),
                mk_order("En A Lon mve Bel"),
                mk_order("En F ENG msup Lon"),
                mk_order("Fr F Bel hsup Nth"),
                mk_order("Ge F Hel msup Ska"),
                mk_order("Ge F Ska mve Nth"),
            ]
        ),
        [
            "En F Nth con Lon !",  # disrupted: the army never moved (fn6)
            "En A Lon hld Bel",  # ambiguous -> stands (fn6), cuts void
            "En F ENG msup Lon",  # given (supports a move that never happened)
            "Fr F Bel hsup Nth",  # NOT cut after all: the fn6 void saved it
            "Ge F Hel msup Ska",  # given
            "Ge F Ska hld Nth !",  # bounces 2v2: Bel's hsup held
        ],
        set(),  # Gilgamesch C.2.1: single-attacker bounce (Ska 2v2) is no Patt
    )


def test_6_f_19_multi_route_convoy_paradox():
    """6.F.19: Tyr is NOT necessary (Ion is an alternative route), so the
    B.3.2.15 filter lets Tun cut Naples' support: Rome bounces 1v1, Tyr
    survives, the Ion route stays alive and Tunis bounces 1v1 at Naples
    (the 2000/Szykman outcome)."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("Fr A Tun mve Nap"),
                mk_order("Fr F Tyr con Tun"),
                mk_order("Fr F Ion con Tun"),
                mk_order("It F Nap msup Rom"),
                mk_order("It F Rom mve Tyr"),
            ]
        ),
        [
            "Fr A Tun hld Nap !",  # bounces 1v1 at the cut-support holder
            "Fr F Tyr con Tun",  # survives: convoy available (army bounced)
            "Fr F Ion con Tun",  # route alive
            "It F Nap hld Rom !",  # CUT: Tyr not necessary (cut supports report hld, cf. writer)
            "It F Rom hld Tyr !",  # bounces 1v1
        ],
        set(),  # Gilgamesch C.2.1: single-attacker bounce (Rom) is no Patt
    )


def test_6_f_20_unwanted_multi_route_convoy_paradox():
    """6.F.20: Ion is NOT necessary (Tyr is the alternative), so Naples'
    hold-support of Ion is cut: Ion is dislodged 2v1, the Tyr route
    stays alive, Tunis bounces 1v1 at Naples."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("Fr A Tun mve Nap"),
                mk_order("Fr F Tyr con Tun"),
                mk_order("Fr F Ion con Tun"),
                mk_order("It F Nap hsup Ion"),
                mk_order("Tu F Aeg msup EMA"),
                mk_order("Tu F EMA mve Ion"),
            ]
        ),
        [
            "Fr A Tun hld Nap !",  # bounces 1v1 at Naples
            "Fr F Tyr con Tun",  # route alive (army bounced at dest)
            "Fr F Ion hld Tun >",  # dislodged: support cut -> 2v1 (post-$cdsl convoyer reports hld)
            "It F Nap hld Ion !",  # hold-support CUT (Ion not necessary)
            "Tu F Aeg msup EMA",  # given
            "Tu F EMA mve Ion",  # succeeds 2v1
        ],
        set(),
    )


def test_6_f_21_dads_army():
    """6.F.21 Dad's Army -- RE-DERIVED outcome (NEEDS_CONTEXT finding, vgl.
    the report): the task table expected the 1982 outcome (Clyde's
    support not cut, NAO survives 2v2), but the cut in this position is
    made by NORWAY, not by Liverpool: Nor->Cly is itself a convoyed move
    (via Nws), and B.3.2.15 -- per its literal text AND the plan's own
    helper ("the cmove's OWN convoyers") -- only bars cutting a support
    that targets a necessary convoyer OF THE CUTTER'S OWN CONVOY. NAO is
    Liverpool's convoyer, not Norway's, so Norway's cut is legal.
    (Liverpool's cut would be B.3.2.15-protected, but under default
    self_cut_ok=False it is not even eligible -- both units are
    English.) Gilgamesch's necessity clause places it with the
    2000/2023EE rule family, i.e. DATC's PREFERRED outcome: Clyde's
    support is cut, NAO is dislodged, Liverpool's route dies (its route
    status diverges between the regimes -> fn6-ambiguous -> it stands)
    and Norway takes Clyde 2v1."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("Ru A Edi msup Nor"),
                mk_order("Ru F Nws con Nor"),
                mk_order("Ru A Nor mve Cly"),
                mk_order("Fr F IRI msup MAO"),
                mk_order("Fr F MAO mve NAO"),
                mk_order("En A Liv mve Cly"),
                mk_order("En F NAO con Liv"),
                mk_order("En F Cly hsup NAO"),
            ]
        ),
        [
            "Ru A Edi msup Nor",  # given
            "Ru F Nws con Nor",  # convoy ran (Nor moved)
            "Ru A Nor mve Cly",  # succeeds 2v1, dislodges the En fleet
            "Fr F IRI msup MAO",  # given
            "Fr F MAO mve NAO",  # succeeds 2v1 (Cly's support cut by Nor)
            "En A Liv hld Cly",  # route dead (NAO dislodged) -> stands, fn6
            "En F NAO hld Liv >",  # dislodged -> disrupted
            "En F Cly hld NAO ! >",  # CUT by Nor (B.3.2.15 does not cross convoys)
        ],
        set(),
    )


def test_6_f_21_dads_army_self_cut_protection_semantics():
    """6.F.21 k1-level probe with self_cut_ok=True -- now LIVERPOOL's cut
    of Clyde's support is eligible too. Pins the B.3.2.15 semantics of
    the re-derived outcome:
    - Norway's cut fires: NAO is NOT a convoyer of Norway's own convoy,
      and (literal B.3.2.15) a hold-support is not protected at all --
      Clyde's hsup is cuttable by ANY eligible cutter.
    - Liverpool's cut attempt finds the support already gone; the
      cut_protected flag stays False (the protection never applied).
    - Liverpool's route status diverges between the regimes -> $fn6."""
    situation = Situation(
        orders=[
            mk_order("Ru A Edi msup Nor"),
            mk_order("Ru F Nws con Nor"),
            mk_order("Ru A Nor mve Cly"),
            mk_order("Fr F IRI msup MAO"),
            mk_order("Fr F MAO mve NAO"),
            mk_order("En A Liv mve Cly"),
            mk_order("En F NAO con Liv"),
            mk_order("En F Cly hsup NAO"),
        ],
        switches=Switches(self_cut_ok=True),
    )
    world = conflict_game_parser(situation)
    dip_eval_mod.k1_evaluation(world)
    cly = world.get_field("Cly")
    assert cly.order == t_order.none  # cut -- by Norway
    assert "$sup_cut" in cly._events
    assert cly.cut_protected is False  # protection does not cross convoys
    nor = world.get_field("Nor")
    assert "$sup_dec" in nor._events  # Nor made the cut
    assert nor.order == t_order.cmove  # active: route alive in both regimes
    nao = world.get_field("NAO")
    assert nao.order == t_order.none  # dislodged in k1 -> $cdsl
    liv = world.get_field("Liv")
    assert liv.order == t_order.none  # ambiguous -> stands (fn6)
    assert "$fn6" in liv._events
    # the full game yields the same Dad's Army outcome as the default switches
    assert_resolution(
        situation,
        [
            "Ru A Edi msup Nor",
            "Ru F Nws con Nor",
            "Ru A Nor mve Cly",
            "Fr F IRI msup MAO",
            "Fr F MAO mve NAO",
            "En A Liv hld Cly",
            "En F NAO hld Liv >",
            "En F Cly hld NAO ! >",
        ],
        set(),
    )


def test_6_f_16_protection_flag():
    """Positive B.3.2.15 machinery probe (6.F.16 Pandin through k1 only):
    Bre is UNAMBIGUOUS (its route lives in both cut regimes -- in the
    optimistic regime its cut of Lon's msup is B.3.2.15-protected, so no
    cut happens at all), so the FINAL pass really attempts the cut: the
    durable cut_protected flag is set ($sup_prot), the support survives
    and the convoyed army still moves (it stays an active cmove)."""
    world = conflict_game_parser(
        Situation(
            orders=[
                mk_order("En F Lon msup Wal"),
                mk_order("En F Wal mve ENG"),
                mk_order("Fr A Bre mve Lon"),
                mk_order("Fr F ENG con Bre"),
                mk_order("Ge F Nth msup Bel"),
                mk_order("Ge F Bel mve ENG"),
            ]
        )
    )
    dip_eval_mod.k1_evaluation(world)
    lon = world.get_field("Lon")
    assert lon.order == t_order.msupport  # NOT cut: attack on the necessary convoyer ENG
    assert lon.cut_protected is True  # durable for k2-k4 ($sup_prot skip)
    assert "$sup_prot" in lon._events
    assert "$sup_cut" not in lon._events
    bre = world.get_field("Bre")
    assert bre.order == t_order.cmove  # active cmove: route alive in both regimes
    assert "$fn6" not in bre._events
    eng = world.get_field("ENG")
    assert eng.order == t_order.convoy  # the 2v2 beleaguered garrison held


################################################
# (b) Footnote 6 ambiguity fallback: DATC 6.F.22 - 6.F.24


def test_6_f_22_second_order_paradox_two_resolutions():
    """6.F.22: two consistent resolutions exist (either both supports are
    cut and both convoys survive, or neither is cut and both convoyers
    are dislodged). The route status of each cmove diverges between the
    optimistic and pessimistic regimes -> both ambiguous -> both armies
    stand, no cuts; Edi and Pic succeed with their supports intact."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("En F Edi mve Nth"),
                mk_order("En F Lon msup Edi"),
                mk_order("Fr A Bre mve Lon"),
                mk_order("Fr F ENG con Bre"),
                mk_order("Ge F Bel msup Pic"),
                mk_order("Ge F Pic mve ENG"),
                mk_order("Ru A Nor mve Bel"),
                mk_order("Ru F Nth con Nor"),
            ]
        ),
        [
            "En F Edi mve Nth",  # succeeds 2v1 (support intact)
            "En F Lon msup Edi",  # NOT cut (fn6: the cut is void)
            "Fr A Bre hld Lon",  # ambiguous -> stands (fn6)
            "Fr F ENG hld Bre >",  # dislodged -> disrupted
            "Ge F Bel msup Pic",  # NOT cut (fn6)
            "Ge F Pic mve ENG",  # succeeds 2v1
            "Ru A Nor hld Bel",  # ambiguous -> stands (fn6)
            "Ru F Nth hld Nor >",  # dislodged -> disrupted
        ],
        set(),
    )


def test_6_f_23_second_order_paradox_two_exclusive_convoys():
    """6.F.23: two EXCLUSIVE resolutions (either convoy survives, never
    both). Route status diverges per cmove between the regimes -> both
    ambiguous -> both stand, no cuts, all four attacks fail on ties and
    nobody is dislodged."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("En F Edi mve Nth"),
                mk_order("En F Yor msup Edi"),
                mk_order("Fr A Bre mve Lon"),
                mk_order("Fr F ENG con Bre"),
                mk_order("Ge F Bel hsup ENG"),
                mk_order("Ge F Lon hsup Nth"),
                mk_order("It F MAO mve ENG"),
                mk_order("It F IRI msup MAO"),
                mk_order("Ru A Nor mve Bel"),
                mk_order("Ru F Nth con Nor"),
            ]
        ),
        [
            "En F Edi hld Nth !",  # 2v2 tie
            "En F Yor msup Edi",  # given (cut void)
            "Fr A Bre hld Lon",  # ambiguous -> stands (fn6, no bounce marker)
            "Fr F ENG con Bre !",  # disrupted: army never moved
            "Ge F Bel hsup ENG",  # given
            "Ge F Lon hsup Nth",  # given
            "It F MAO hld ENG !",  # 2v2 tie
            "It F IRI msup MAO",  # given
            "Ru A Nor hld Bel",  # ambiguous -> stands (fn6)
            "Ru F Nth con Nor !",  # disrupted: army never moved
        ],
        set(),  # Gilgamesch C.2.1: single-attacker ties (Edi, MAO) are no Patt
    )


def test_6_f_24_second_order_paradox_no_resolution():
    """6.F.24: NO consistent resolution exists (the cut of the Belgium
    support both requires and forbids itself). Route status diverges per
    cmove -> both ambiguous -> both stand, no cuts: Edi dislodges Nth
    2v1, the Irish Sea attack ties 2v2 against ENG's intact
    hold-support."""
    assert_resolution(
        Situation(
            orders=[
                mk_order("En F Edi mve Nth"),
                mk_order("En F Lon msup Edi"),
                mk_order("En F IRI mve ENG"),
                mk_order("En F MAO msup IRI"),
                mk_order("Fr A Bre mve Lon"),
                mk_order("Fr F ENG con Bre"),
                mk_order("Fr F Bel hsup ENG"),
                mk_order("Ru A Nor mve Bel"),
                mk_order("Ru F Nth con Nor"),
            ]
        ),
        [
            "En F Edi mve Nth",  # succeeds 2v1 (Lon's support intact)
            "En F Lon msup Edi",  # NOT cut (fn6)
            "En F IRI hld ENG !",  # 2v2 tie (Bel's hsup intact)
            "En F MAO msup IRI",  # given
            "Fr A Bre hld Lon",  # ambiguous -> stands (fn6)
            "Fr F ENG con Bre !",  # disrupted: army never moved
            "Fr F Bel hsup ENG",  # given (cut void)
            "Ru A Nor hld Bel",  # ambiguous -> stands (fn6)
            "Ru F Nth hld Nor >",  # dislodged -> disrupted
        ],
        set(),  # Gilgamesch C.2.1: single-attacker bounce (IRI 2v2) is no Patt
    )


################################################
# Snapshot machinery: the 3-pass design must not leak state between passes.


def test_model_copy_deep_copies_private_events():
    """k1 snapshots the world via t_field.model_copy(deep=True). The
    private `_events` list MUST be copied per instance -- a shared list
    would leak the discarded optimistic/pessimistic pass events into the
    final state (and mutate the snapshot itself)."""
    field = t_field(player="En", order=t_order.none, dest="X", xref="X", strength=1, name="Lon")
    field.add_event("ev1")
    copy_ = field.model_copy(deep=True)
    assert copy_._events is not field._events  # independent lists
    copy_.add_event("ev2")
    assert field._events == ["ev1"]  # original untouched
    assert copy_._events == ["ev1", "ev2"]


def test_k1_passes_do_not_leak_discarded_cuts():
    """6.F.22 through k1 only: the OPTIMISTIC pass cuts both supports (no
    B.3.2.15 protection -- each support targets the OTHER convoy's
    fleet). The discarded optimistic state must not survive: after the
    final (fn6) pass both supports are intact and no $sup_cut/$fn6-pass
    events leaked into the kept fields."""
    world = conflict_game_parser(
        Situation(
            orders=[
                mk_order("En F Edi mve Nth"),
                mk_order("En F Lon msup Edi"),
                mk_order("Fr A Bre mve Lon"),
                mk_order("Fr F ENG con Bre"),
                mk_order("Ge F Bel msup Pic"),
                mk_order("Ge F Pic mve ENG"),
                mk_order("Ru A Nor mve Bel"),
                mk_order("Ru F Nth con Nor"),
            ]
        )
    )
    dip_eval_mod.k1_evaluation(world)
    lon = world.get_field("Lon")
    bel = world.get_field("Bel")
    assert lon.order == t_order.msupport  # support survived
    assert bel.order == t_order.msupport
    assert not any(ev.startswith("$sup_cut") for ev in lon._events + bel._events)
    assert not any(ev.startswith("$sup_dec") for ev in lon._events + bel._events)
    # the two ambiguous armies stand (fn6 pre-demotion in the final pass)
    assert world.get_field("Bre").order == t_order.none
    assert world.get_field("Nor").order == t_order.none
    assert "$fn6" in world.get_field("Bre")._events
    # and the convoys themselves were not marked fcategory repeatedly
    assert world.get_field("ENG")._events.count("$k1f") == 1
    assert world.get_field("Nth")._events.count("$k1f") == 1


def test_final_pass_monotonicity_reiteration(caplog):
    """Synthetic third-order case for the bounded re-iteration guard (max 3
    final passes). The optimistic-vs-pessimistic route comparison classifies
    C as ACTIVE (its convoyer F1 survives both extreme regimes: in the
    optimistic regime C's own cut weakens the attack on F1, in the
    pessimistic regime the intact hold-support defends it). But in the FINAL
    regime the AMBIGUOUS cmove X stands, which RESTORES the attack support
    that X would have cut (DX's msup of A->F1): together with the still-cut
    hold-support of F1 (cut by the active C3) this dislodges F1 -- so C's
    route dies in the final pass although it survived both extremes.
    The guard must then drop C from the active set and re-run the final
    pass: C stands ($fn6) and its cut of D1's support is void (D1 keeps its
    msup, A2 wins 2v1 at FX). Without the re-iteration, C's cut of D1 would
    wrongly survive and FX would wrongly stand."""
    world = conflict_game_parser(
        Situation(
            orders=[
                mk_order("P A C mve D1"),  # cmove via F1; cuts D1's msup of A2->FX
                mk_order("P F F1 con C"),
                mk_order("Q A D1 msup A2"),  # supports A2->FX; sits at C's dest
                mk_order("S A X mve DX"),  # cmove via FX; AMBIGUOUS (FX dies only w/o cuts)
                mk_order("S F FX con X"),
                mk_order("T A DX msup A"),  # supports A->F1; restored when X stands
                mk_order("W A A mve F1"),  # attacker of F1
                mk_order("U A C3 mve D3"),  # cmove via F3; cuts D3's hsup of F1
                mk_order("U F F3 con C3"),
                mk_order("V A D3 hsup F1"),  # defends F1; sits at C3's dest
                mk_order("Y A A2 mve FX"),  # attacker of FX
            ]
        )
    )
    with caplog.at_level(logging.WARNING, logger="dipworkpy.eval.eval_k1"):
        dip_eval_mod.k1_evaluation(world)
    assert "unstable" in caplog.text  # the guard fired exactly for C
    assert "['C']" in caplog.text
    # C was dropped from the active set and stands via fn6; its cut is void
    c = world.get_field("C")
    assert c.order == t_order.none
    assert "$fn6" in c._events
    assert "$sup_dec" not in c._events
    # D1's msup survives the voided cut -> A2 dislodges FX 2v1
    d1 = world.get_field("D1")
    assert d1.order == t_order.msupport
    assert "$sup_cut" not in d1._events
    fx = world.get_field("FX")
    assert fx.order == t_order.none  # $cdsl: dislodged by A2
    # the third convoy is unaffected: C3 stays active and keeps its cut
    c3 = world.get_field("C3")
    assert c3.order == t_order.cmove
    assert "$sup_dec" in c3._events
    assert world.get_field("D3").order == t_order.none  # hsup cut by C3
    assert world.get_field("F3").order == t_order.convoy  # route intact


################################################
################################################

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    pytest.main(sys.argv + ["-vv"])
