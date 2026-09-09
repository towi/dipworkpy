"""Architectural invariant: subfields (split coasts) never reach the conflict engine.

Geography (GEO-008) must normalize every subfield reference (SpN, SpS, BuS, ...)
to its superfield (Spa, Bul, ...) BEFORE the order set flows into the conflict
resolver. These tests enforce that invariant at three levels: the map protocol,
the geography phase output, and the full round pipeline.
"""

from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType
from dipworkpy.round.orchestrator import RoundRequest, round_full


def _standard_map():
    return resolve_map_ref(MapRef())


def _all_fields(m):
    """Enumerate the field names of the map.

    MapProtocol has no field_names(); fields are recovered from the edge
    endpoints (both directions) plus a closure over subfields, so subfields
    are found even if one had no borders of its own.
    """
    fields = set()
    for frm, to, _edge in m.edge_items():
        fields.add(frm)
        fields.add(to)
    frontier = list(fields)
    while frontier:
        fld = frontier.pop()
        for sub in m.subfields_of(fld):
            if sub not in fields:
                fields.add(sub)
                frontier.append(sub)
    return fields


def _subfield_pairs(m):
    """All (subfield, superfield) pairs of the map, sorted for stable output."""
    pairs = []
    for fld in sorted(_all_fields(m)):
        for sub in m.subfields_of(fld):
            pairs.append((sub, fld))
    return pairs


def test_every_subfield_normalizes_to_its_superfield():
    m = _standard_map()
    pairs = _subfield_pairs(m)
    # The standard map has split coasts; a vacuous pass would hide a regression.
    assert pairs, "standard map unexpectedly has no subfields"
    for sub, sup in pairs:
        assert m.superfield_of(sub) == sup, f"{sub} should normalize to {sup}"


def test_geography_output_orders_are_superfield_only():
    m = _standard_map()
    pairs = _subfield_pairs(m)
    assert pairs, "standard map unexpectedly has no subfields"
    subfield_names = {sub for sub, _sup in pairs}

    hold_orders = [Order(nation="En", utype="F", current=sub, order=OrderType.hld, dest=None) for sub, _sup in pairs]
    res = geography_phase(GeographyRequest(orders=hold_orders, map=MapRef()))

    assert len(res.orders) == len(hold_orders)
    for out in res.orders:
        assert out.current not in subfield_names, f"subfield {out.current!r} leaked into geography output"
        if out.dest is not None:
            assert out.dest not in subfield_names, f"subfield {out.dest!r} leaked into geography output"


def test_round_full_moves_and_conflicts_on_superfields():
    # F on the north coast of Spa holds; Fr A Gas moves to Spa.
    # The F's order collapses SpN -> Spa, so the conflict for Spa must be
    # resolved on the superfield: the engine never sees 'SpN'.
    req = RoundRequest(
        orders=[
            Order(nation="En", utype="F", current="SpN", order=OrderType.hld, dest=None),
            Order(nation="Fr", utype="A", current="Gas", order=OrderType.mve, dest="Spa"),
        ],
        unit_positions={"SpN": ("En", "F"), "Gas": ("Fr", "A")},
    )
    res = round_full(req)
    currents = {o.current for o in res.conflict.resolution.orders}
    assert "SpN" not in currents, "subfield 'SpN' reached the conflict engine"
    assert "Spa" in currents, "expected the collapsed superfield 'Spa' in the conflict"
