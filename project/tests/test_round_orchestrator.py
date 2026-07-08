"""End-to-end tests for round_full.

round_full chains syntax → geography → conflict and is the canonical
consumer of the new service trio. These tests exercise it across the
spectrum of order outcomes (success, bounce, support cut, dislodgement)
plus the B.4.2.9 / B.4.2.10 asymmetry that geography_phase markers
propagate into conflict resolution.
"""

from dipworkpy.model import Order, OrderType
from dipworkpy.round.orchestrator import round_full, RoundRequest


def _orders_by_field(round_result):
    """Helper: dict from current-field name to OrderResult for easy lookups."""
    return {o.current: o for o in round_result.conflict.resolution.orders}


def test_full_round_passes_through_phases():
    req = RoundRequest(
        orders=[Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh")],
        unit_positions={"Vie": ("Au", "A")},
    )
    res = round_full(req)
    assert res.syntax is not None
    assert res.geography is not None
    assert res.conflict is not None
    # geography emits per-order diagnostics on the happy path; syntax only
    # emits when something is struck or a hold-default is injected.
    phases = {d.phase for d in res.diagnostics}
    assert "geography" in phases


def test_full_round_syn008_hold_default_reaches_conflict():
    # Mun has a unit but no order; SYN-008 should inject a hold-default,
    # and the conflict phase should report Mun as holding (no movement).
    req = RoundRequest(
        orders=[Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh")],
        unit_positions={"Vie": ("Au", "A"), "Mun": ("Ge", "A")},
    )
    res = round_full(req)
    by_field = _orders_by_field(res)
    assert "Mun" in by_field
    # SYN-008 produced a hold; conflict should leave Mun's unit alive and
    # holding in place (no dislodge, no failure)
    assert by_field["Mun"].dislodged is None
    assert by_field["Mun"].succeeds is None
    # the SYN-008 diagnostic should be in the merged trail
    assert any(d.rule == "SYN-008" for d in res.diagnostics)


def test_full_round_simple_bounce():
    # Vie → Tyr, Mun → Tyr. Equal-strength bounce, both fail, no dislodge.
    req = RoundRequest(
        orders=[
            Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Tyr"),
            Order(nation="Ge", utype="A", current="Mun", order=OrderType.mve, dest="Tyr"),
        ],
        unit_positions={"Vie": ("Au", "A"), "Mun": ("Ge", "A")},
    )
    res = round_full(req)
    by = _orders_by_field(res)
    assert by["Vie"].succeeds is False
    assert by["Mun"].succeeds is False


def test_full_round_support_move_succeeds():
    # Vie → Boh, Tyr supports. Lone defender at Boh dislodged.
    req = RoundRequest(
        orders=[
            Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh"),
            Order(nation="Au", utype="A", current="Tyr", order=OrderType.msup, dest="Vie"),
            Order(nation="Ge", utype="A", current="Boh", order=OrderType.hld),
        ],
        unit_positions={
            "Vie": ("Au", "A"),
            "Tyr": ("Au", "A"),
            "Boh": ("Ge", "A"),
        },
    )
    res = round_full(req)
    by = _orders_by_field(res)
    assert by["Vie"].succeeds is None  # move succeeded (sparse: None)
    assert by["Boh"].dislodged is True


def test_full_round_b429_invalid_mve_not_hold_supportable():
    # B.4.2.9: an invalid mve (target ZZZ) leaves the unit in place but
    # NOT hold-supportable. A neighbour's hsup is ineffective.
    # Setup: Vie tries mve ZZZ (invalid), Tyr hsup Vie, Mun attacks Vie.
    # Expected: Vie dislodged because hsup doesn't apply to a 'moving' unit
    # whose move failed geographically.
    req = RoundRequest(
        orders=[
            Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="ZZZ"),
            Order(nation="Au", utype="A", current="Tyr", order=OrderType.hsup, dest="Vie"),
            Order(nation="Ge", utype="A", current="Boh", order=OrderType.mve, dest="Vie"),
            Order(nation="Ge", utype="A", current="Sil", order=OrderType.msup, dest="Boh"),
        ],
        unit_positions={
            "Vie": ("Au", "A"),
            "Tyr": ("Au", "A"),
            "Boh": ("Ge", "A"),
            "Sil": ("Ge", "A"),
        },
    )
    res = round_full(req)
    by = _orders_by_field(res)
    # Vie's invalid mve was geography-flagged as holds_no_support,
    # so the conflict resolver should treat hsup-from-Tyr as inert
    # and let the Boh attack (with Sil support) dislodge Vie.
    assert by["Vie"].dislodged is True


def test_full_round_b4210_invalid_sup_holds_supportable():
    # B.4.2.10: an invalid hsup (target ZZZ) makes the unit hold AND
    # the unit IS hold-supportable. A neighbour's hsup IS effective.
    # Setup: Vie has invalid hsup ZZZ, Tyr hsup Vie, Mun attacks Vie.
    # Expected: Vie survives because Tyr's hsup applies (Vie is a holder).
    req = RoundRequest(
        orders=[
            Order(nation="Au", utype="A", current="Vie", order=OrderType.hsup, dest="ZZZ"),
            Order(nation="Au", utype="A", current="Tyr", order=OrderType.hsup, dest="Vie"),
            Order(nation="Ge", utype="A", current="Boh", order=OrderType.mve, dest="Vie"),
        ],
        unit_positions={
            "Vie": ("Au", "A"),
            "Tyr": ("Au", "A"),
            "Boh": ("Ge", "A"),
        },
    )
    res = round_full(req)
    by = _orders_by_field(res)
    # Vie's invalid hsup was geography-flagged as holds_supportable,
    # Tyr's valid hsup applies, Vie survives.
    assert by["Vie"].dislodged is None


def test_full_round_emits_geo007_diagnostic_for_resolved_coast():
    # F Spa mve LYO — coast resolution should record SpS and emit GEO-007.
    req = RoundRequest(
        orders=[Order(nation="Fr", utype="F", current="Spa", order=OrderType.mve, dest="LYO")],
        unit_positions={"Spa": ("Fr", "F")},
    )
    res = round_full(req)
    assert any(d.rule == "GEO-007" for d in res.diagnostics)
