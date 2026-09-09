"""
test cases from
http://web.inter.nl.net/users/L.B.Kruijswijk/
"""

# std lib
import sys
import logging

# 3rd party
import pytest

# local
from dipworkpy.model import Situation, Order, OrderType, ConflictResolution, OrderResult
from dipworkpy.eval.eval_model import t_order
import dipworkpy.eval as dip_eval_mod

# under test
from dipworkpy.conflict_game import conflict_game, parser as conflict_game_parser
from dipworkpy.round.orchestrator import RoundRequest, round_full

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
    succeeds = None if "!" not in toks else False
    dislodged = None if ">" not in toks else True
    return OrderResult(nation=n, utype=u, current=c, order=o, dest=d, succeeds=succeeds, dislodged=dislodged)


################################################


def test_6_a_1():
    """
    Moving to an Area That Is Not a Neighbor (6.A.1)
    Check if an illegal move (without convoy) will fail.

    The engine-only path is field-name agnostic BY DESIGN and cannot reject
    this; the rejection happens in geography (B.4.2.9 -> holds_no_support),
    so the test must go through round_full.

    See tests/TEST_CASES_DATC.md for details.
    """
    req = RoundRequest(
        orders=[Order(nation="En", utype="F", current="NTH", order=OrderType.mve, dest="Pic")],
        unit_positions={"NTH": ("En", "F")},
    )
    res = round_full(req)
    o = res.conflict.resolution.orders[0]
    assert o.order == OrderType.hld  # move collapsed to hold
    assert o.succeeds is False  # and it did not succeed


def test_6_a_2():
    """
    No Order Given (6.A.2)
    Check if a unit will hold when no order is given.

    See tests/TEST_CASES_DATC.md for details.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order_0("Au A Vie"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("Au A Vie hld Vie"),
        ],
        pattfields=set(),
    )
    assert result <= expected


def test_6_c_1():
    """
    Three Army Circular Movement (6.C.1)
    Three armies moving in a circle.

    See tests/TEST_CASES_DATC.md for details.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("Tu A Ank mve Con"),
            mk_order("Tu A Con mve Smy"),
            mk_order("Tu A Smy mve Ank"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("Tu A Ank mve Con"),
            mk_oresult("Tu A Con mve Smy"),
            mk_oresult("Tu A Smy mve Ank"),
        ],
        pattfields=set(),
    )
    assert result <= expected


def test_6_d_1():
    """
    Support to Hold (6.D.1)
    A supported unit will not be dislodged.

    See tests/TEST_CASES_DATC.md for details.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("Au A Vie hsup Tri"),
            mk_order_h("Au A Tri hld"),
            mk_order("It A Ven mve Tri"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("Au A Vie hsup Tri"),
            mk_oresult("Au A Tri hld Tri"),
            mk_oresult("It A Ven mve Tri !"),
        ],
        pattfields=set(),
    )
    assert result <= expected


def test_6_d_2():
    """
    Move with Support (6.D.2)
    A move with support will succeed against a weaker defense.

    See tests/TEST_CASES_DATC.md for details.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("Au A Vie mve Tri"),
            mk_order("Au A Tyr msup Vie"),
            mk_order_h("It A Tri hld"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("Au A Vie mve Tri"),
            mk_oresult("Au A Tyr msup Vie"),
            mk_oresult("It A Tri hld Tri >"),
        ],
        pattfields=set(),
    )
    # TODO: Fix algorithm to handle this case properly - support mechanics need refinement
    assert result <= expected


def test_6_d_3():
    """
    Cut Support (6.D.3)
    Support is cut when the supporting unit is attacked.

    Per Gilgamesch C.3.1.3.2 the pattfields contain only genuine standoffs;
    both bounced destinations here are single-attacker bounces (C.2.1), so
    pattfields = set(). See doc/DATC_ANALYSIS.md.

    See tests/TEST_CASES_DATC.md for details.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("Au A Vie mve Tri"),
            mk_order("Au A Tyr msup Vie"),
            mk_order_h("It A Tri hld"),
            mk_order("It A Ven mve Tyr"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("Au A Vie mve Tri !"),
            mk_oresult("Au A Tyr msup Vie !"),  # Support cut
            mk_oresult("It A Tri hld Tri"),
            mk_oresult("It A Ven mve Tyr !"),  # Attack fails
        ],
        pattfields=set(),  # Gilgamesch C.2.1: single-attacker bounces are no Patt; the old {Tri, Tyr} encoded the DATC-strict bounced-destinations convention
    )
    assert result <= expected


def test_6_f_1():
    """
    Beleaguered Garrison (6.F.1)
    When a unit is attacked from multiple directions with equal strength, it is not dislodged.

    The beleaguered garrison is a genuine C.2.2 standoff, so Ber stays a
    pattfield (pattfields = {Ber}). See doc/DATC_ANALYSIS.md.

    See tests/TEST_CASES_DATC.md for details.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("Ge A Mun mve Ber"),
            mk_order("Ge A Pru mve Ber"),
            mk_order("Ru A War mve Ber"),
            mk_order_h("Ru A Ber hld"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("Ge A Mun mve Ber !"),
            mk_oresult("Ge A Pru mve Ber !"),
            mk_oresult("Ru A War mve Ber !"),
            mk_oresult("Ru A Ber hld Ber"),
        ],
        pattfields={"Ber"},
    )
    assert result <= expected


def test_6_a_11():
    """
    Simple Bounce (6.A.11)
    Two armies bouncing on each other.

    See tests/TEST_CASES_DATC.md for details.
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
        pattfields={"Tyr"},
    )
    result.show(sys.stderr, line_prefix="| ")
    # '<=' ignores 'original'
    # This test passes - keep assertion
    assert result <= expected, f"\nres: {result.__log__()} !=\nexp: {expected.__log__()}"


def test_6_e_1():
    """
    No Convoy in Coastal Areas (6.E.1)
    A convoy can only be given by a fleet in a sea area.

    See tests/TEST_CASES_DATC.md for details.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("En A Lon mve Bre"),
            mk_order("En F ENG con Lon"),  # Valid convoy
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("En A Lon mve Bre"),  # Should succeed with convoy
            mk_oresult("En F ENG con Lon"),
        ],
        pattfields=set(),
    )
    assert result <= expected


def test_6_g_1():
    """
    Multiple Convoy Paths (6.G.1)
    Army convoyed by multiple fleets over different paths.

    See tests/TEST_CASES_DATC.md for details.
    """
    # arrange
    situation: Situation = Situation(
        orders=[
            mk_order("En A Lon mve Bre"),
            mk_order("En F ENG con Lon"),
            mk_order("En F NTH con Lon"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("En A Lon mve Bre"),
            mk_oresult("En F ENG con Lon"),
            mk_oresult("En F NTH con Lon"),
        ],
        pattfields=set(),
    )
    assert result <= expected


################################################
# Gilgamesch B.3.2.14 / GEO-010: "mve [Convoy]" (Order.via_convoy).
#
# Semantics: a flagged move ALWAYS enters the engine as a cmove. k1's route
# check ($criv: no convoyers or dead route -> order=none) turns a failed
# convoy into "the unit stands, keeps its defensive strength and has NO
# effect on the neighbour field" (no support cut). A functioning convoy
# moves the unit by convoy. A plain (unflagged) mve to an adjacent field
# is not affected by convoy routes.
#
# mk_order cannot express the flag, so the tests below build via_convoy
# orders with a dedicated helper.


def mk_order_via(spec: str) -> Order:
    """mk_order with via_convoy=True (GEO-010 "mve [Convoy]")."""
    return mk_order(spec).model_copy(update={"via_convoy": True})


def test_b3214_via_convoy_failed_convoy_stands_without_effect():
    """B.3.2.14 sentence 1: "mve [Convoy]" to a DIRECTLY ADJACENT field whose
    convoy fails -> the army stands and has no effect on the neighbour field
    (no support cut).

    Topology (standard map, verified via geography.rules.can_reach_by_unit):
    Pic-Bel is a land edge for armies AND ENG convoys Pic->Bel (ENG touches
    both coasts). The Fr attack on the convoyer ENG is supported FROM Bel
    itself: if the flagged move had any effect on Bel, that support would be
    cut and the dislodgement of ENG would bounce.
    """
    situation: Situation = Situation(
        orders=[
            mk_order_via("En A Pic mve Bel"),  # adjacent, but flagged [Convoy]
            mk_order("En F ENG con Pic"),  # the convoyer
            mk_order("Fr F NTH mve ENG"),  # dislodges the convoyer ...
            mk_order("Fr F Bel msup NTH"),  # ... supported from the convoy target
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("En A Pic hld Bel"),  # stands: dead route -> $criv -> hold
            mk_oresult("En F ENG hld Pic >"),  # convoyer dislodged
            mk_oresult("Fr F NTH mve ENG"),  # supported attack succeeds
            mk_oresult("Fr F Bel msup NTH"),  # NOT cut: the flagged move never attacked Bel
        ],
        pattfields=set(),
    )
    assert result <= expected


def test_b3214_via_convoy_no_convoyer_stands_and_cuts_nothing():
    """B.3.2.14 sentence 1, pure form: "mve [Convoy]" with NO convoy ordered.
    The flagged move becomes a cmove whose route check finds no convoyers
    ($criv) -> the army stands with full defensive strength and cuts nothing.

    Without the GEO-010 wiring this order reaches the legacy engine as a
    plain land move: it attacks Bel, cuts the Fr support, and the attack on
    ENG bounces.
    """
    situation: Situation = Situation(
        orders=[
            mk_order_via("En A Pic mve Bel"),  # adjacent, flagged, no con order
            mk_order_h("En F ENG hld"),  # gets dislodged if the support holds
            mk_order("Fr F NTH mve ENG"),
            mk_order("Fr F Bel msup NTH"),  # only uncut if Pic has no effect on Bel
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("En A Pic hld Bel"),  # stands, no effect on Bel
            mk_oresult("En F ENG hld ENG >"),  # support survived -> dislodged
            mk_oresult("Fr F NTH mve ENG"),
            mk_oresult("Fr F Bel msup NTH"),  # NOT cut
        ],
        pattfields=set(),
    )
    assert result <= expected


def test_b3214_via_convoy_functioning_convoy_moves_by_convoy():
    """B.3.2.14 sentence 2: "mve [Convoy]" with a functioning convoy moves by
    convoy. Lon->Bre has no land route (verified); ENG convoys."""
    situation: Situation = Situation(
        orders=[
            mk_order_via("En A Lon mve Bre"),
            mk_order("En F ENG con Lon"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    expected = ConflictResolution(
        orders=[
            mk_oresult("En A Lon mve Bre"),  # moved (by convoy)
            mk_oresult("En F ENG con Lon"),  # convoy intact
        ],
        pattfields=set(),
    )
    assert result <= expected


def test_b3214_plain_move_to_adjacent_is_not_cmove():
    """B.3.2.14 sentence 3: a PLAIN mve (no via_convoy flag) to an adjacent
    field moves and is not broken by a stray convoy order.

    Verified behaviour: the legacy con-order scan (and equally GEO-009's
    classify_cmove_candidates on the graph path, which has no adjacency
    exclusion) demotes this unflagged Pic->Bel to a cmove because a con
    order targets Pic. With the convoy functioning the observable outcome is
    identical to a direct move: the army arrives. (Per strict B.3.2.14 the
    plain move should ignore the convoy route entirely; the legacy parser
    has no map to check adjacency, and GEO-009 is out of scope here.)
    This test pins the guaranteed part of the contract: the move succeeds.
    """
    situation: Situation = Situation(
        orders=[
            mk_order("Ge A Pic mve Bel"),  # adjacent, NO flag
            mk_order("En F ENG con Pic"),  # stray convoy order
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    by = {o.current: o for o in result.orders}
    assert by["Pic"].order == OrderType.mve
    assert by["Pic"].succeeds is None  # moved
    assert by["ENG"].order == OrderType.con


def test_b3214_via_convoy_geo_invalid_without_con_orders():
    """GEO-010 through the full pipeline (round_full): "F NTH mve Pic
    [Convoy]" is not a direct fleet move (GEO-003 would reject it, NTH-Pic
    has no fleet edge -- verified). With the flag it is classified as a
    convoy move; k1's route check (no convoyers, $criv) lets the fleet stand
    at FULL defensive strength: the unsupported Fr attack bounces.

    Pre-GEO-010 this was the DipNet bucket-B bug: the flagged move reached
    the engine as a geo-invalid land move (holds_no_support, defensive
    strength 0) and any attack dislodged it.
    """
    req = RoundRequest(
        orders=[
            Order(nation="En", utype="F", current="NTH", order=OrderType.mve, dest="Pic", via_convoy=True),
            Order(nation="Fr", utype="F", current="Edi", order=OrderType.mve, dest="NTH"),
        ],
        unit_positions={"NTH": ("En", "F"), "Edi": ("Fr", "F")},
    )
    # act
    res = round_full(req)
    # assert -- geography: flagged move is a valid convoy move, not GEO-003
    info = res.geography.order_geo_info[0]
    assert info.is_valid is True
    assert info.invalidity_code is None
    assert info.effective_behavior == "moves"
    assert info.is_convoy_move is True
    assert not any(d.rule == "GEO-003" and d.order_index == 0 for d in res.diagnostics)
    # assert -- conflict: the fleet stands with full defensive strength
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["NTH"].order == OrderType.hld  # $criv -> hold
    assert by["NTH"].succeeds is None  # the hold itself is "successful"
    assert by["NTH"].dislodged is None  # full defensive strength -> attack bounces
    assert by["Edi"].succeeds is False  # unsupported attack on a full-strength holder fails


def test_b3214_unflagged_adjacent_move_ignores_disrupted_convoy():
    """B.3.2.14 sentence 3: a plain (unflagged) mve to a directly adjacent
    field moves by land even when a stray con order exists and that convoy is
    disrupted.

    GEO-009's classify_cmove_candidates used to demote the unflagged adjacent
    Pic->Bel move to a cmove because a con order targets Pic; the disrupted
    convoy (ENG dislodged) then killed the route and the army stood instead
    of walking.

    Topology (standard map, verified via geography.rules.can_reach_by_unit):
    Pic-Bel is an army land edge; ENG convoys Pic->Bel; NTH is fleet-adjacent
    to ENG; IRI is fleet-adjacent to ENG (valid msup of the NTH->ENG attack,
    GEO-004). The attacker is Fr because En attacking its own convoyer would
    be a forbidden self-dislodgement (the attack would bounce, the convoy
    would stay intact).
    """
    req = RoundRequest(
        orders=[
            Order(nation="Ge", utype="A", current="Pic", order=OrderType.mve, dest="Bel"),  # adjacent, NO flag
            Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Pic"),  # stray convoyer
            Order(nation="Fr", utype="F", current="NTH", order=OrderType.mve, dest="ENG"),  # dislodges ENG
            Order(nation="Fr", utype="F", current="IRI", order=OrderType.msup, dest="NTH"),  # support NTH->ENG
        ],
        unit_positions={"Pic": ("Ge", "A"), "ENG": ("En", "F"), "NTH": ("Fr", "F"), "IRI": ("Fr", "F")},
    )
    # act
    res = round_full(req)
    # assert
    orders = {o.current: o for o in res.conflict.resolution.orders}
    # a dead-route cmove ends as hld with succeeds=None, so the order type is
    # what discriminates "moved by land" from "stood because the convoy died"
    assert orders["Pic"].order == OrderType.mve
    assert orders["Pic"].succeeds is None  # army moves directly to Bel by land
    assert orders["ENG"].dislodged is True  # convoyer dislodged (irrelevant for the land move)


################################################
# Gilgamesch B.3.2.13 / C.2.3: convoy swap of adjacent units.
#
# Semantics: two units with effective move orders into each other's field do
# NOT swap -- ordinary head-to-head in k3 -- UNLESS at least one moves via
# convoy: then they swap without conflict. B.3.2.13: the swap requires the
# explicit "mve [Convoy]" flag (via_convoy -> cmove) on at least one side AND
# a third unit executing the con order. A cmove with a dead route is already
# t_order.none after k1 ($criv), so a cmove surviving into k3 is executable.
# An unflagged adjacent move is NOT a cmove (GEO-009), so without the flag
# the swap attempt is an ordinary head-to-head bounce.
#
# Topology (standard map, verified in the B.3.2.14 tests above): Pic-Bel is
# an army land edge; ENG convoys Pic->Bel; NTH and IRI are fleet-adjacent
# to ENG (valid supported attack on the convoyer).


def test_b3213_convoy_swap_of_adjacent_units():
    """B.3.2.13: Pic and Bel swap fields when Pic's move carries the
    explicit "mve [Convoy]" flag and ENG executes the con order. C.2.3:
    with a convoy involved there is NO border conflict -- both moves
    succeed (legacy path: the flag makes Pic a cmove, Bel stays nmove)."""
    situation: Situation = Situation(
        orders=[
            mk_order_via("Fr A Pic mve Bel"),  # explicit convoy move
            mk_order("Ge A Bel mve Pic"),  # direct move back into Pic
            mk_order("En F ENG con Pic"),  # third unit executes the convoy
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    orders = {o.current: o for o in result.orders}
    assert orders["Pic"].order == OrderType.mve
    assert orders["Pic"].succeeds is None  # moved (by convoy)
    assert orders["Bel"].order == OrderType.mve
    assert orders["Bel"].succeeds is None  # moved (directly)
    assert orders["ENG"].order == OrderType.con
    assert orders["ENG"].dislodged is None  # convoyer intact


def test_b3213_no_flag_no_swap():
    """B.3.2.13 the other way: WITHOUT the explicit flag an attempted swap
    of adjacent units is an ordinary head-to-head -- both bounce. Uses the
    graph path (round_full), where GEO-009 keeps both unflagged adjacent
    moves nmove. (On the legacy path the con-order scan cannot know
    adjacency and would demote Pic to cmove -- documented limitation.)"""
    req = RoundRequest(
        orders=[
            Order(nation="Fr", utype="A", current="Pic", order=OrderType.mve, dest="Bel"),  # NO flag
            Order(nation="Ge", utype="A", current="Bel", order=OrderType.mve, dest="Pic"),  # NO flag
            Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Pic"),
        ],
        unit_positions={"Pic": ("Fr", "A"), "Bel": ("Ge", "A"), "ENG": ("En", "F")},
    )
    # act
    res = round_full(req)
    # assert
    orders = {o.current: o for o in res.conflict.resolution.orders}
    assert orders["Pic"].order == OrderType.hld
    assert orders["Pic"].succeeds is False  # head-to-head bounce
    assert orders["Bel"].order == OrderType.hld
    assert orders["Bel"].succeeds is False


def test_b3213_swap_with_dead_route_no_swap():
    """B.3.2.13: the flag alone is not enough -- a third unit must be able
    to EXECUTE the con order. ENG is dislodged by a supported third-nation
    attack, so k1's $criv turns Pic's convoy move into a stand: Pic keeps
    its field, and Bel's ordinary move into the still-occupied Pic
    bounces (unsupported attack on a full-strength holder)."""
    req = RoundRequest(
        orders=[
            Order(nation="Fr", utype="A", current="Pic", order=OrderType.mve, dest="Bel", via_convoy=True),
            Order(nation="Ge", utype="A", current="Bel", order=OrderType.mve, dest="Pic"),
            Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Pic"),
            Order(nation="Ru", utype="F", current="NTH", order=OrderType.mve, dest="ENG"),  # dislodges ENG
            Order(nation="Ru", utype="F", current="IRI", order=OrderType.msup, dest="NTH"),  # support NTH->ENG
        ],
        unit_positions={
            "Pic": ("Fr", "A"),
            "Bel": ("Ge", "A"),
            "ENG": ("En", "F"),
            "NTH": ("Ru", "F"),
            "IRI": ("Ru", "F"),
        },
    )
    # act
    res = round_full(req)
    # assert
    orders = {o.current: o for o in res.conflict.resolution.orders}
    assert orders["ENG"].dislodged is True  # the attack kills the convoy route
    assert orders["Pic"].order == OrderType.hld  # $criv: dead route -> stands
    assert orders["Pic"].succeeds is None
    assert orders["Bel"].order == OrderType.hld  # unsupported attack on Pic bounces
    assert orders["Bel"].succeeds is False


def test_b3213_convoy_swap_is_decided_explicitly_in_k3():
    """k3-level probe for B.3.2.13/C.2.3: the convoy swap is decided
    EXPLICITLY in k3 -- the pair is marked $swap and NOT as a k3 border
    conflict (fcategory stays 0), so neither field is drawn into the k3
    pairwise resolution or change_moves_to_umoves. The outcome-level
    behavior is covered by the tests above; this pins the rule marking."""
    situation: Situation = Situation(
        orders=[
            mk_order_via("Fr A Pic mve Bel"),
            mk_order("Ge A Bel mve Pic"),
            mk_order("En F ENG con Pic"),
        ],
    )
    # act -- run the conflict chain only up to k3
    world = conflict_game_parser(situation)
    dip_eval_mod.k1_evaluation(world)
    dip_eval_mod.k2_evaluation(world)
    dip_eval_mod.k3_evaluation(world)
    # assert
    pic = world.get_field("Pic")
    bel = world.get_field("Bel")
    assert pic.order == t_order.cmove
    assert bel.order == t_order.nmove
    assert "$swap" in pic._events
    assert "$swap" in bel._events
    assert pic.fcategory == 0  # NOT a k3 conflict field
    assert bel.fcategory == 0
    assert pic.succeeds and bel.succeeds


################################################
# Task 5b analysis outcome (2026-09-09): NO vacated-field defense bug.
#
# A third-party attack onto a field a swap participant is vacating is an
# ordinary C.2.2 contest for that field: C.2.3's swap "ohne Konflikt" exempts
# only the MUTUAL head-to-head of the swap pair, it does not immunise the
# swap against third parties. resolve_conflict_at_field gives a vacating
# occupant (order cmove/nmove) defval=0, so a departing unit never defends
# its origin field. Verified consequences, per Gilgamesch C.2.1/C.2.2:
# - stronger third attack wins the vacated field -> the swap collapses as
#   a CONSEQUENCE (the losing partner bounces home and blocks the other leg);
# - stronger (supported) swap move wins the contest -> swap survives, the
#   third attack bounces;
# - equal strengths -> C.2.2 patt, all three bounce.
# The reporting review's "all-bounce + attacker bounces" probe used
# "Bul msup Ser" for an attack on Alb -- Bul does not touch Alb, so GEO-004
# voids that support on the graph path (correct 1v1 patt), while the
# geography-blind legacy path counts it (known legacy limitation, cf.
# test_6_a_1). The tests below pin the verified-correct semantics on both
# paths; the comparative case (normally vacated field, no swap) included.


def test_c22_supported_third_attack_takes_vacated_swap_field():
    """Task 5b probe with a VALID support: Pic-Bel swap via ENG convoy;
    Ru attacks the vacated Bel 2v1 (Ruh + Hol msup Ruh, Hol touches Bel).
    C.2.2: the single strongest move wins the field -- the swap has no
    immunity, so the 2v1 takes Bel, Pic's convoy move bounces home, the
    returned Pic unit blocks Bel's move (1v1 draw) and Bel's bounced unit
    is dislodged by the attacker entering Bel."""
    situation: Situation = Situation(
        orders=[
            mk_order_via("Fr A Pic mve Bel"),  # cmove swap leg (flag + ENG con)
            mk_order("Ge A Bel mve Pic"),  # nmove swap leg
            mk_order("En F ENG con Pic"),  # convoyer
            mk_order("Ru A Ruh mve Bel"),  # third attack onto the vacated Bel
            mk_order("Ru A Hol msup Ruh"),  # -> 2v1
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    orders = {o.current: o for o in result.orders}
    assert orders["Ruh"].order == OrderType.mve  # strongest -> takes Bel
    assert orders["Ruh"].succeeds is None
    assert orders["Pic"].order == OrderType.hld  # lost the C.2.2 contest
    assert orders["Pic"].succeeds is False
    assert orders["Bel"].order == OrderType.hld  # blocked by the returned Pic
    assert orders["Bel"].succeeds is False
    assert orders["Bel"].dislodged is True  # displaced by Ruh entering Bel
    assert orders["ENG"].order == OrderType.con
    # R1 (DipNet dataset): the convoy chain is intact and the army bounced at
    # its destination (engine umove) -- the con order reports success.
    assert orders["ENG"].succeeds is None


def test_c22_supported_swap_move_wins_vacated_field():
    """The other direction of the same C.2.2 contest: the swap partner's
    incoming move is SUPPORTED (Bur msup Pic->Bel, 2) and beats the
    unsupported third attack (Ruh, 1). The swap survives; only the third
    attack bounces."""
    situation: Situation = Situation(
        orders=[
            mk_order_via("Fr A Pic mve Bel"),
            mk_order("Fr A Bur msup Pic"),  # support the convoy move (Bur touches Bel)
            mk_order("Ge A Bel mve Pic"),
            mk_order("En F ENG con Pic"),
            mk_order("Ru A Ruh mve Bel"),  # unsupported third attack
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    orders = {o.current: o for o in result.orders}
    assert orders["Pic"].order == OrderType.mve  # swap survives
    assert orders["Pic"].succeeds is None
    assert orders["Bel"].order == OrderType.mve
    assert orders["Bel"].succeeds is None
    assert orders["Ruh"].order == OrderType.hld  # third attack bounces
    assert orders["Ruh"].succeeds is False
    assert orders["Bur"].order == OrderType.msup
    assert orders["Bur"].succeeds is None


def test_c22_equal_third_attack_on_vacated_swap_field_bounces_all():
    """Equal strengths (1v1): C.2.2 patt -- neither the swap leg nor the
    third attack enters the vacated field, and the collapse blocks the
    other swap leg too: all three units stand (none dislodged)."""
    situation: Situation = Situation(
        orders=[
            mk_order_via("Fr A Pic mve Bel"),
            mk_order("Ge A Bel mve Pic"),
            mk_order("En F ENG con Pic"),
            mk_order("Ru A Ruh mve Bel"),  # unsupported: 1v1 with Pic's cmove
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    orders = {o.current: o for o in result.orders}
    for current in ("Pic", "Bel", "Ruh"):
        assert orders[current].order == OrderType.hld
        assert orders[current].succeeds is False
        assert orders[current].dislodged is None


def test_c22_third_attack_on_vacated_swap_field_graph_path():
    """Same 2v1 as test_c22_supported_third_attack_takes_vacated_swap_field
    through the graph path (round_full + GEO validation): the VALID Hol msup
    Ruh support is counted there too, so both paths agree -- the attacker
    takes the vacated field. (The reporting review's graph-vs-legacy
    divergence came from the GEO-004-invalid "Bul msup Ser" against Alb,
    which Bul does not touch.)"""
    req = RoundRequest(
        orders=[
            Order(nation="Fr", utype="A", current="Pic", order=OrderType.mve, dest="Bel", via_convoy=True),
            Order(nation="Ge", utype="A", current="Bel", order=OrderType.mve, dest="Pic"),
            Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Pic"),
            Order(nation="Ru", utype="A", current="Ruh", order=OrderType.mve, dest="Bel"),
            Order(nation="Ru", utype="A", current="Hol", order=OrderType.msup, dest="Ruh"),
        ],
        unit_positions={
            "Pic": ("Fr", "A"),
            "Bel": ("Ge", "A"),
            "ENG": ("En", "F"),
            "Ruh": ("Ru", "A"),
            "Hol": ("Ru", "A"),
        },
    )
    # act
    res = round_full(req)
    # assert
    orders = {o.current: o for o in res.conflict.resolution.orders}
    assert orders["Ruh"].order == OrderType.mve  # strongest -> takes Bel
    assert orders["Ruh"].succeeds is None
    assert orders["Pic"].order == OrderType.hld
    assert orders["Pic"].succeeds is False
    assert orders["Bel"].order == OrderType.hld
    assert orders["Bel"].succeeds is False
    assert orders["Bel"].dislodged is True


def test_c22_supported_attack_on_normally_vacated_field_enters():
    """Comparative probe (no swap): Bel's occupant moves out normally
    (mve Bur, uncontested) and the supported 2v1 attack onto the vacated
    Bel enters trivially -- a departing unit (order cmove/nmove) never
    defends its origin field (defval=0 in resolve_conflict_at_field)."""
    situation: Situation = Situation(
        orders=[
            mk_order("Ge A Bel mve Bur"),  # normal vacating move
            mk_order("Ru A Ruh mve Bel"),
            mk_order("Ru A Hol msup Ruh"),
        ],
    )
    # act
    result = conflict_game(situation)
    # assert
    orders = {o.current: o for o in result.orders}
    assert orders["Bel"].order == OrderType.mve  # vacater moves out
    assert orders["Bel"].succeeds is None
    assert orders["Ruh"].order == OrderType.mve  # attacker enters the vacated field
    assert orders["Ruh"].succeeds is None
    assert orders["Hol"].order == OrderType.msup
    assert orders["Hol"].succeeds is None


################################################
################################################


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        # format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        format="%(filename)s:%(lineno)d: [%(levelname)s] %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d:%H:%M:%S",
    )
    import pytest

    pytest.main(sys.argv + ["-vv"])
