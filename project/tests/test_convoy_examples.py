"""Convoy edge-case tests, one per CV-id from doc/convoy_examples.md.

Each test:
  1. Loads the corresponding `.dwex` file from doc/examples/convoy/.
  2. Builds an inline map + Situation from the DDL (so the test does not
     rely on the bundled standard map).
  3. Routes the request through `round_full`, which exercises the full
     pipeline: syntax → geography (incl. cmove classification + convoy
     graph extraction) → conflict resolver (which uses the convoy graph
     in eval_k1 instead of the legacy `convoy_routing_engine='always'`).
  4. Asserts the case-specific invariant (who moves, who is dislodged,
     which diagnostic codes fired).

This is a deliberately verbose layout — one test function per edge case
makes the failure messages name the rule under test. The general
parametrized regression in `tests/test_dwex_examples.py` does not pick
these files up because they live outside the `dwex/` tree.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pytest

from dipworkpy.geo_model import MapRef
from dipworkpy.model import OrderType, Switches
from dipworkpy.round.orchestrator import RoundRequest, RoundResult, round_full
from dipworkpy.tools.dwex.lang import parse_file
from dipworkpy.tools.dwex.to_map import to_map_definition
from dipworkpy.tools.dwex.to_situation import to_situation

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "doc/examples/convoy"


def _unit_positions(doc) -> Dict[str, Tuple[str, str]]:
    """Derive unit_positions from the DDL's order list (each order
    targets exactly one unit at its `current` field)."""
    return {u.current: (u.nation, u.utype) for u in doc.units}


def _run(stem: str) -> RoundResult:
    path = EXAMPLES_DIR / f"{stem}.dwex"
    doc = parse_file(path)
    map_def = to_map_definition(doc)
    req = RoundRequest(
        orders=to_situation(doc).orders,
        unit_positions=_unit_positions(doc),
        map=MapRef(inline_map=map_def),
        switches=Switches(),
    )
    return round_full(req)


def _by_field(res: RoundResult) -> Dict[str, object]:
    return {o.current: o for o in res.conflict.resolution.orders}


def _diag_rules(res: RoundResult):
    return {d.rule for d in res.diagnostics}


def _move_was_downgraded(o) -> bool:
    """True if the result is a hold but the original order was a move.

    The conflict resolver downgrades failed mve / cmove orders to t_order.none
    in the internal model; the writer then emits OrderType.hld with
    succeeds=None (the hold itself was 'successful' — the unit stayed put).
    This helper packages the post-condition check in one place.
    """
    return (
        o.order == OrderType.hld
        and o.original is not None
        and o.original.order == OrderType.mve
    )


# ---------------------------------------------------------------------------
# CV-01 — Basic convoy
# ---------------------------------------------------------------------------
def test_CV01_basic_convoy_succeeds():
    res = _run("CV-01_basic")
    by = _by_field(res)
    # army arrived at its destination
    assert by["Lon"].dest == "Bel"
    assert by["Lon"].succeeds is None  # sparse-success
    # convoyer kept its field
    assert by["NTH"].dislodged is None


# ---------------------------------------------------------------------------
# CV-02 — Convoyer on a land field (Gilgamesch B.3.2.1 / GEO-005)
# ---------------------------------------------------------------------------
def test_CV02_convoyer_on_land_rejected_by_geography():
    res = _run("CV-02_convoyer_on_land")
    by = _by_field(res)
    # army downgraded to a (successful) hold — its mve failed
    assert _move_was_downgraded(by["Lon"])
    assert by["Lon"].dislodged is None
    # convoyer held (its con was downgraded to a hold under B.4.2.10)
    assert by["Wal"].dislodged is None
    # GEO-005 must appear in the audit trail
    assert "GEO-005" in _diag_rules(res)


# ---------------------------------------------------------------------------
# CV-03 — Convoyer not adjacent to dest (GEO-006)
# ---------------------------------------------------------------------------
def test_CV03_convoyer_not_adjacent_rejected_by_geography():
    res = _run("CV-03_convoyer_not_adjacent")
    by = _by_field(res)
    assert _move_was_downgraded(by["Lon"])
    assert "GEO-006" in _diag_rules(res)


# ---------------------------------------------------------------------------
# CV-04 — Convoy disrupted by dislodgement (Gilgamesch B.3.2.12)
# ---------------------------------------------------------------------------
def test_CV04_dislodged_convoyer_breaks_chain():
    res = _run("CV-04_disrupted_by_dislodgement")
    by = _by_field(res)
    # convoyer dislodged
    assert by["NTH"].dislodged is True
    # army's mve was downgraded to a hold (the convoy fell apart)
    assert _move_was_downgraded(by["Kie"])


# ---------------------------------------------------------------------------
# CV-05 — Convoyer attacked but not dislodged (B.3.2.12 contrapositive)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    reason=(
        "k1 convoy-attacker dislodgement loop doesn't run the actual strength "
        "comparison: any nmove targeting a fcategory=1 convoyer is treated as "
        "successful, regardless of the convoyer's defensive_strength or hold "
        "support. Real Diplomacy rules require the attacker to strictly exceed "
        "the convoyer's defensive strength (incl. hold-supporters). Fixing "
        "this needs a small restructure of eval_k1.k1_evaluation — the "
        "conflict should be resolved at the convoyer's field, not at the "
        "attacker's. Documented as a known limitation."
    ),
    strict=True,
)
def test_CV05_convoy_survives_equal_attack():
    res = _run("CV-05_survives_bounce")
    by = _by_field(res)
    # The CORRECT outcome: NTH defended by its own strength plus MID's hsup
    # totals 2; ENG's unsupported attack at strength 1 should bounce.
    assert by["NTH"].dislodged is None
    assert by["ENG"].succeeds is False
    assert by["Lon"].dest == "Bel"
    assert by["Lon"].succeeds is None


# ---------------------------------------------------------------------------
# CV-06 — Redundant disconnected convoyer doesn't disturb the working chain
# ---------------------------------------------------------------------------
def test_CV06_disconnected_extra_convoyer_is_ignored():
    res = _run("CV-06_redundant_convoyer")
    by = _by_field(res)
    # army arrived via the connected convoyer (NTH)
    assert by["Edi"].dest == "Bel"
    assert by["Edi"].succeeds is None
    # disconnected convoyer just held
    assert by["ION"].dislodged is None


# ---------------------------------------------------------------------------
# CV-07 — Chain of two fleets (pairwise sea adjacency)
# ---------------------------------------------------------------------------
def test_CV07_two_fleet_relay_chain():
    res = _run("CV-07_chain_of_two")
    by = _by_field(res)
    # army arrived
    assert by["Lon"].dest == "Nor"
    assert by["Lon"].succeeds is None
    # both convoyers still in place
    assert by["NTH"].dislodged is None
    assert by["NWS"].dislodged is None


# ---------------------------------------------------------------------------
# CV-08 — Foreign nation convoy (B.3.2.10 nation notation)
# ---------------------------------------------------------------------------
def test_CV08_english_convoys_french_army():
    res = _run("CV-08_foreign_nation")
    by = _by_field(res)
    # army arrived, nation stayed French
    assert by["Lon"].dest == "Bel"
    assert by["Lon"].succeeds is None
    assert by["Lon"].nation == "Fr"
    # convoyer stayed English
    assert by["NTH"].nation == "En"
    assert by["NTH"].dislodged is None
