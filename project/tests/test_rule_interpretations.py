"""
Characterization tests for the Gilgamesch rule-interpretation switches in
dipworkpy.model.Switches:
- rule_interpretation_IX_3 (values 0/1/2): self-dislodgement-with-defender's-nation-
  support semantics (Gilgamesch IX.3).
- rule_interpretation_IX_7 (values 0/1/2): head-to-head (k3 border conflict)
  variants for the effect of the losing/drawing move (Gilgamesch IX.7).
- self_cut_ok (False/True): whether a same-nation attack cuts a support.

DATC case numbers were VERIFIED against testdata/datc-v3/DATC_v3_2.html (extracted
with the same tag-stripping as the DATC triage, see tests/test_conflict_datc.py):

IX_3 -- DATC v3.2 section 6.D/6.E family ("the defender's nation supports the
attacker -> that support is void for the dislodgement of its own unit"):
- 6.D.10 "SELF DISLODGMENT PROHIBITED" / 6.D.11 "NO SELF DISLODGMENT OF RETURNING
  UNIT" -- the underlying prohibition.
- 6.D.12 "SUPPORTING A FOREIGN UNIT TO DISLODGE OWN UNIT PROHIBITED" / 6.D.13
  (idem, returning unit) -- the void-support rule; engine: strength_b in
  eval_common.count_supporters excludes supports of the attacked field's nation.
- 6.E.12 "SUPPORT ON ATTACK ON OWN UNIT CAN BE USED FOR OTHER MEANS" -- the void
  support still counts among the attackers (strength_a); causes the standoff.
- 6.D.14 "SUPPORTING A FOREIGN UNIT IS NOT ENOUGH TO PREVENT DISLODGMENT".
The 0/1/2 value split itself (which of several attackers wins) is Gilgamesch
IX.3; the DATC only decides the single-attacker case.

IX_7 -- the DATC v3.2 head-to-head family is section 6.E ("HEAD-TO-HEAD BATTLES
AND BELEAGUERED GARRISON"), NOT 6.C (circular movement):
- 6.E.4 "NON-DISLODGED LOSER STILL HAS EFFECT", 6.E.5 "LOSER DISLODGED BY ANOTHER
  ARMY STILL HAS EFFECT", 6.E.6 "NOT DISLODGE BECAUSE OF OWN SUPPORT STILL HAS
  EFFECT" -- value 0 (the default) implements these; values 1/2 are Gilgamesch
  IX.7 variants without DATC counterpart.

self_cut_ok -- DATC v3.2 6.D.20 "UNIT CANNOT CUT SUPPORT OF ITS OWN COUNTRY":
the default False is the DATC position (a same-nation attack does not cut);
True is the Gilgamesch variant where it does cut.

All topologies use standard-map fields and go through round_full, so every
order is geography-validated (GEO-001..004, incl. the Gilgamesch B.3.1.1 rule
that a supporter must be able to reach the supported target itself).
"""

# std lib
from typing import Dict, Optional, Set, Tuple

# 3rd party
import pytest

# local
from dipworkpy.model import Order, ConflictResolution, OrderResult, Switches
from dipworkpy.round.orchestrator import RoundRequest, round_full

################################################


def mk_order(spec: str) -> Order:
    nation, utype, current, ordertype, dest = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=ordertype, dest=dest)


def mk_order_h(spec: str) -> Order:
    """hold order without dest field."""
    nation, utype, current, ordertype = spec.split()
    return Order(nation=nation, utype=utype, current=current, order=ordertype, dest=None)


def mk_oresult(s: str) -> OrderResult:
    """@:param s -- order description to parse, eg "Ge A Vie hld Mun !", "Ge A Vie mve Mun".
    Add "!" to mark the order as "not succeeded" and ">" as "dislodged".
    """
    toks = s.split()
    n, u, c, o, d = toks[0:5]
    succeeds = None if "!" not in toks else False
    dislodged = None if ">" not in toks else True
    return OrderResult(nation=n, utype=u, current=c, order=o, dest=d, succeeds=succeeds, dislodged=dislodged)


def assert_resolution(
    orders,
    unit_positions: Dict[str, Tuple[str, str]],
    expected_orders,
    expected_pattfields: Set[str],
    **switches: Optional[int],
) -> None:
    """Strict full-resolution assertion through the FULL round pipeline
    (syntax + geography + conflict), so every order in the topologies is
    verified as geography-legal. Compares with clear_originals() + `==`
    (strict), like tests/test_convoy_paradox.py:assert_resolution.
    """
    req = RoundRequest(
        orders=orders,
        unit_positions=unit_positions,
        switches=Switches(**switches),
    )
    res = round_full(req)
    for d in res.diagnostics:
        assert d.message == "ok", f"non-ok diagnostic: {d.message}"
    result: ConflictResolution = res.conflict.resolution
    result.clear_originals()
    expected = ConflictResolution(
        orders=[mk_oresult(o) for o in expected_orders],
        pattfields=expected_pattfields,
    )
    expected.clear_originals()
    assert result == expected, f"\nres: {result.__log__()}\n!=\nexp: {expected.__log__()}"


################################################
# IX_3: DATC anchors (value-independent)


@pytest.mark.parametrize("ri93", [0, 1, 2])
def test_ri93_datc_6d12_void_support_single_attacker(ri93):
    """DATC 6.D.12 'SUPPORTING A FOREIGN UNIT TO DISLODGE OWN UNIT PROHIBITED':
    Austria supports the Italian attack on its own F Trieste. The support is
    void for the dislodgement (strength_b), so the single attacker bounces --
    for ALL three IX_3 values (the value split only matters with several
    attackers; the DATC decides only this single-attacker case)."""
    assert_resolution(
        [
            mk_order_h("Au F Tri hld"),
            mk_order("Au A Vie msup Ven"),  # defender-nation support -> b-void
            mk_order("It A Ven mve Tri"),
        ],
        {"Tri": ("Au", "F"), "Vie": ("Au", "A"), "Ven": ("It", "A")},
        [
            "Au F Tri hld Tri",
            "Au A Vie msup Ven",
            "It A Ven hld Tri !",
        ],
        set(),
        rule_interpretation_IX_3=ri93,
    )


@pytest.mark.parametrize("ri93", [0, 1, 2])
def test_ri93_datc_6e12_void_support_counts_among_attackers(ri93):
    """DATC 6.E.12 'SUPPORT ON ATTACK ON OWN UNIT CAN BE USED FOR OTHER MEANS':
    Austrian A Serbia supports the Italian attack on (own) Budapest -- void for
    the dislodgement, but it STILL counts in the attacker-vs-attacker strength
    comparison (strength_a): Italy (2) and Russia (2) stand off at Budapest, so
    nobody dislodges the Austrian unit. Without the Serbian support Russia (2)
    would win against the defense of 1. Value-independent (winner_a is a draw,
    the IX.3 branch is never reached). Also mirrors the DATC 6.D.17/18 flavor:
    the fleeing A Budapest bounces against the attacked supporter A Rumania."""
    assert_resolution(
        [
            mk_order("Au A Bud mve Rum"),
            mk_order("Au A Ser msup Vie"),  # defender-nation support -> b-void
            mk_order("It A Vie mve Bud"),
            mk_order("Ru A Gal mve Bud"),
            mk_order("Ru A Rum msup Gal"),
        ],
        {"Bud": ("Au", "A"), "Ser": ("Au", "A"), "Vie": ("It", "A"), "Gal": ("Ru", "A"), "Rum": ("Ru", "A")},
        [
            "Au A Bud hld Rum !",
            "Au A Ser msup Vie",
            "It A Vie hld Bud !",
            "Ru A Gal hld Bud !",
            "Ru A Rum msup Gal",
        ],
        {"Bud"},
        rule_interpretation_IX_3=ri93,
    )


################################################
# IX_3: the three values, pairwise distinguished
#
# No single k4 topology separates all three values: in the k4 chain loop
# ($chain4) values 0 and 2 CONVERGE -- after the losing attackers become umove,
# the a-winner is re-checked alone and value 0 rejects it exactly like value 2
# unless its own b-strength beats the defense. Value 1 is the strictest (the
# same attacker must also win the b-comparison among the ORIGINAL attackers).
# Value 0 differs from 1/2 only in the k2 single-shot resolution (attacked
# supporter, DATC 6.D.17/18). Hence three scenarios:
# - Gilgamesch example topology (all values bounce -- documents the 0==2
#   convergence the _ri_9_3 docstring text does not predict),
# - k4 topology separating value 1 from {0, 2},
# - k2 topology separating value 0 from {1, 2}.


@pytest.mark.parametrize("ri93", [0, 1, 2])
def test_ri93_k4_gilgamesh_example_all_values_bounce(ri93):
    """The Gilgamesch IX.3 example from the _ri_9_3 docstring, translated to
    GEO-legal standard-map orders (Ge's support of Bel must come from a FLEET
    that can reach ENG itself, hence F Bre instead of an army): En F ENG holds,
    England (the defender's nation!) supports the French attack twice (b-void),
    Germany also attacks ENG with one own support. First resolution: Fr a=3
    wins, Ge b=2 would win cleanly. Per the docstring, value 0 should let
    Fr F MID-ENG succeed -- but the k4 chain loop re-resolves ENG after Ge's
    umove and rejects the lone Fr attack (b=1 vs defval=1) in ALL values.
    Characterization of the engine, not of the Gilgamesch intent."""
    assert_resolution(
        [
            mk_order_h("En F ENG hld"),
            mk_order("En F NTH msup MID"),  # defender-nation support -> b-void
            mk_order("En F Lon msup MID"),  # defender-nation support -> b-void
            mk_order("Fr F MID mve ENG"),  # a=3, b=1
            mk_order("Ge F Bel mve ENG"),  # a=2, b=2
            mk_order("Ge F Bre msup Bel"),
        ],
        {
            "ENG": ("En", "F"),
            "NTH": ("En", "F"),
            "Lon": ("En", "F"),
            "MID": ("Fr", "F"),
            "Bel": ("Ge", "F"),
            "Bre": ("Ge", "F"),
        },
        [
            "En F ENG hld ENG",
            "En F NTH msup MID",
            "En F Lon msup MID",
            "Fr F MID hld ENG !",
            "Ge F Bel hld ENG !",
            "Ge F Bre msup Bel",
        ],
        set(),
        rule_interpretation_IX_3=ri93,
    )


def test_ri93_k4_value1_strictest():
    """k4 topology separating value 1 from {0, 2}: En F NTH holds; England
    (defender's nation) supports the FRENCH attack on NTH twice (b-void);
    Germany attacks NTH with two own supports. Fr ENG: a=4, b=2; Ge Den:
    a=3, b=3; defval=1. The a-winner is Fr, the b-winner is Ge.
    - value 0: the b-winner (Ge) is an attacker, so Fr's dislodgement stands;
      the $chain4 re-check of the lone Fr attack passes (b=2 > 1) -> Fr wins.
    - value 1: the b-winner is NOT the a-winner -> rejected -> standoff.
    - value 2: Fr's own b-strength (2) beats the defense -> Fr wins."""
    orders = [
        mk_order_h("En F NTH hld"),
        mk_order("En F Edi msup ENG"),  # defender-nation support -> b-void
        mk_order("En F Yor msup ENG"),  # defender-nation support -> b-void
        mk_order("Fr F ENG mve NTH"),  # a=4 (1+Edi+Yor+Bel), b=2 (Bel)
        mk_order("Fr F Bel msup ENG"),
        mk_order("Ge F Den mve NTH"),  # a=3 (1+SKA+HEL), b=3
        mk_order("Ge F SKA msup Den"),
        mk_order("Ge F HEL msup Den"),
    ]
    units = {
        "NTH": ("En", "F"),
        "Edi": ("En", "F"),
        "Yor": ("En", "F"),
        "ENG": ("Fr", "F"),
        "Bel": ("Fr", "F"),
        "Den": ("Ge", "F"),
        "SKA": ("Ge", "F"),
        "HEL": ("Ge", "F"),
    }
    for ri93 in (0, 2):
        assert_resolution(
            orders,
            units,
            [
                "En F NTH hld NTH >",
                "En F Edi msup ENG",
                "En F Yor msup ENG",
                "Fr F ENG mve NTH",
                "Fr F Bel msup ENG",
                "Ge F Den hld NTH !",
                "Ge F SKA msup Den",
                "Ge F HEL msup Den",
            ],
            set(),
            rule_interpretation_IX_3=ri93,
        )
    assert_resolution(
        orders,
        units,
        [
            "En F NTH hld NTH",
            "En F Edi msup ENG",
            "En F Yor msup ENG",
            "Fr F ENG hld NTH !",
            "Fr F Bel msup ENG",
            "Ge F Den hld NTH !",
            "Ge F SKA msup Den",
            "Ge F HEL msup Den",
        ],
        set(),
        rule_interpretation_IX_3=1,
    )


def test_ri93_k2_value0_dislodges_anyway():
    """k2 topology separating value 0 from {1, 2}: Ru F Nor supports Ru F
    ENG->NTH and is attacked by the very unit it supports against (Ge F NTH
    counter-moves to Nor) -- the k2 single-shot resolution case behind DATC
    6.D.17/6.D.18. Russia (the defender's nation at Nor!) supports the German
    counter-move twice (b-void); England attacks Nor with one own support.
    Ge F NTH: a=3, b=1; En F NWS: a=2, b=2; defval(Nor)=1.
    - value 0: 'the occupant would be dislodged anyway' -- En's clean b=2
      beats the defense, so the a-winner Ge F NTH dislodges Nor and Ru F ENG
      follows into the vacated NTH.
    - values 1/2: rejected -> everything bounces (Nor survives; its support is
      cut by En F NWS's bounced attack in k4, a DATC 6.D.3-style cut)."""
    orders = [
        mk_order("Ru F Nor msup ENG"),
        mk_order("Ru F ENG mve NTH"),
        mk_order("Ge F NTH mve Nor"),  # counter-move -> k2 single-shot at Nor
        mk_order("Ru F BAR msup NTH"),  # defender-nation support -> b-void
        mk_order("Ru A Fin msup NTH"),  # defender-nation support -> b-void
        mk_order("En F NWS mve Nor"),  # a=2 (1+SKA), b=2
        mk_order("En F SKA msup NWS"),
    ]
    units = {
        "Nor": ("Ru", "F"),
        "ENG": ("Ru", "F"),
        "NTH": ("Ge", "F"),
        "BAR": ("Ru", "F"),
        "Fin": ("Ru", "A"),
        "NWS": ("En", "F"),
        "SKA": ("En", "F"),
    }
    assert_resolution(
        orders,
        units,
        [
            "Ru F Nor hld ENG ! >",
            "Ru F ENG mve NTH",
            "Ge F NTH mve Nor",
            "Ru F BAR msup NTH",
            "Ru A Fin msup NTH",
            "En F NWS hld Nor !",
            "En F SKA msup NWS",
        ],
        set(),
        rule_interpretation_IX_3=0,
    )
    for ri93 in (1, 2):
        assert_resolution(
            orders,
            units,
            [
                "Ru F Nor hld ENG !",
                "Ru F ENG hld NTH !",
                "Ge F NTH hld Nor !",
                "Ru F BAR msup NTH",
                "Ru A Fin msup NTH",
                "En F NWS hld Nor !",
                "En F SKA msup NWS",
            ],
            set(),
            rule_interpretation_IX_3=ri93,
        )


################################################
# IX_7: the three values, pairwise distinguished
#
# No single topology separates all three values: in the border-DECIDED case
# values 1 and 2 behave identically (the losing move is voided), in the
# border-DRAW case values 0 and 1 behave identically (both drawing moves stay
# active). Hence two scenarios: a draw (separates 2) and the DATC 6.E.5 mirror
# (separates 0).


def test_ri97_border_draw_value2_voids_both_moves():
    """Head-to-head DRAW (Fr F Bel <-> Ge F Hol, 1v1) plus a third attack on
    one of the poles (En A Kie -> Hol, 1). In the draw the drawing moves stay
    active for values 0/1: Fr F Bel's continuing attack on Hol ties with Kie
    -> standoff at Hol, Kie bounces. Value 2 ('the opposing moves have no
    effect') voids Fr F Bel's move first, so Kie is the lone attacker and
    dislodges Ge F Hol. NB: the $patt marking of both poles is unconditional,
    so Hol ends up in pattfields even though Kie enters it."""
    orders = [
        mk_order("Fr F Bel mve Hol"),
        mk_order("Ge F Hol mve Bel"),
        mk_order("En A Kie mve Hol"),
    ]
    units = {"Bel": ("Fr", "F"), "Hol": ("Ge", "F"), "Kie": ("En", "A")}
    for ri97 in (0, 1):
        assert_resolution(
            orders,
            units,
            [
                "Fr F Bel hld Hol !",
                "Ge F Hol hld Bel !",
                "En A Kie hld Hol !",
            ],
            {"Bel", "Hol"},
            rule_interpretation_IX_7=ri97,
        )
    assert_resolution(
        orders,
        units,
        [
            "Fr F Bel hld Hol !",
            "Ge F Hol hld Bel ! >",
            "En A Kie mve Hol",
        ],
        {"Bel", "Hol"},
        rule_interpretation_IX_7=2,
    )


def test_ri97_datc_6e5_mirror_value0_loses_effect_at_1_2():
    """DATC 6.E.5 'LOSER DISLODGED BY ANOTHER ARMY STILL HAS EFFECT', mirrored
    on the standard map: Ge F Hol->NTH (3) beats Fr F NTH->Hol (2) at the
    border; En F NWS->NTH (4) then dislodges the French loser at NTH, so the
    German winner cannot enter NTH. Austria's A Ruh->Hol (2) ties with the
    French loser's continuing attack on Hol (2) -> standoff at Hol.
    - value 0 (default, DATC-conformant per 6.E.4/6.E.5/6.E.6): the losing
      Fr F NTH->Hol stays active, Ruhr bounces, Hol is a standoff; the German
      fleet at Hol survives -- exactly the DATC outcome.
    - values 1/2: the losing move is voided ($mlooseA), so Ruhr is the lone
      attacker on the vacating Hol and dislodges Ge F Hol -- CONTRA 6.E.5.
    This is the engine characterization of the Gilgamesch IX.7 variants; the
    DATC head-to-head family in DATC v3.2 is section 6.E, not 6.C."""
    orders = [
        mk_order("Ge F Hol mve NTH"),
        mk_order("Ge F HEL msup Hol"),
        mk_order("Ge F SKA msup Hol"),
        mk_order("Fr F NTH mve Hol"),
        mk_order("Fr F Bel msup NTH"),
        mk_order("En F NWS mve NTH"),
        mk_order("En F Edi msup NWS"),
        mk_order("En F Yor msup NWS"),
        mk_order("En F Lon msup NWS"),
        mk_order("Au A Ruh mve Hol"),
        mk_order("Au A Kie msup Ruh"),
    ]
    units = {
        "Hol": ("Ge", "F"),
        "HEL": ("Ge", "F"),
        "SKA": ("Ge", "F"),
        "NTH": ("Fr", "F"),
        "Bel": ("Fr", "F"),
        "NWS": ("En", "F"),
        "Edi": ("En", "F"),
        "Yor": ("En", "F"),
        "Lon": ("En", "F"),
        "Ruh": ("Au", "A"),
        "Kie": ("Au", "A"),
    }
    assert_resolution(
        orders,
        units,
        [
            "Ge F Hol hld NTH !",
            "Ge F HEL msup Hol",
            "Ge F SKA msup Hol",
            "Fr F NTH hld Hol ! >",
            "Fr F Bel msup NTH",
            "En F NWS mve NTH",
            "En F Edi msup NWS",
            "En F Yor msup NWS",
            "En F Lon msup NWS",
            "Au A Ruh hld Hol !",
            "Au A Kie msup Ruh",
        ],
        {"Hol"},
        rule_interpretation_IX_7=0,
    )
    for ri97 in (1, 2):
        assert_resolution(
            orders,
            units,
            [
                "Ge F Hol hld NTH ! >",
                "Ge F HEL msup Hol",
                "Ge F SKA msup Hol",
                "Fr F NTH hld Hol ! >",
                "Fr F Bel msup NTH",
                "En F NWS mve NTH",
                "En F Edi msup NWS",
                "En F Yor msup NWS",
                "En F Lon msup NWS",
                "Au A Ruh mve Hol",
                "Au A Kie msup Ruh",
            ],
            set(),
            rule_interpretation_IX_7=ri97,
        )


################################################
# self_cut_ok


def test_self_cut_ok_default_false_datc_6d20_and_true_variant():
    """The _ri_sc_ok example topology (Gilgamesch): Fr F MID-ENG supported by
    Fr F Bre, attacked from own A Pic-Bre, against En F ENG holding.
    - default False = DATC 6.D.20 'UNIT CANNOT CUT SUPPORT OF ITS OWN
      COUNTRY': the same-nation attack does NOT cut, Fr enters ENG with 2v1.
    - True: the own-nation attack cuts the support ($sup_cut), Fr bounces 1v1.
    Also documents the model defaults (DATC-conformant positions)."""
    assert Switches().self_cut_ok is False
    assert Switches().rule_interpretation_IX_3 == 0
    assert Switches().rule_interpretation_IX_7 == 0
    orders = [
        mk_order("Fr F MID mve ENG"),
        mk_order("Fr F Bre msup MID"),
        mk_order("Fr A Pic mve Bre"),  # same-nation attack on own supporter
        mk_order_h("En F ENG hld"),
    ]
    units = {"MID": ("Fr", "F"), "Bre": ("Fr", "F"), "Pic": ("Fr", "A"), "ENG": ("En", "F")}
    assert_resolution(
        orders,
        units,
        [
            "Fr F MID mve ENG",
            "Fr F Bre msup MID",
            "Fr A Pic hld Bre !",
            "En F ENG hld ENG >",
        ],
        set(),
        self_cut_ok=False,
    )
    assert_resolution(
        orders,
        units,
        [
            "Fr F MID hld ENG !",
            "Fr F Bre hld MID !",
            "Fr A Pic hld Bre !",
            "En F ENG hld ENG",
        ],
        set(),
        self_cut_ok=True,
    )
