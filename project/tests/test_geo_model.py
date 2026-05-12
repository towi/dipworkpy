"""Tests for shared geo-model types."""
import pytest
from pydantic import ValidationError

from dipworkpy.geo_model import (
    FieldType, Passable, Edge, MapDefinition, MapRef,
    OrderGeoInfo, ConvoyGraph,
)


def test_field_type_enum_values():
    assert FieldType.LA.value == "LA"
    assert FieldType.LCB.value == "LCB"
    assert FieldType.LCA.value == "LCA"
    assert FieldType.LC.value == "LC"
    assert FieldType.LCF.value == "LCF"
    assert FieldType.L.value == "L"
    assert FieldType.O.value == "O"
    assert FieldType.COL.value == "COL"


def test_passable_enum_values():
    assert Passable.YES.value == "ja"
    assert Passable.NO.value == "nein"
    assert Passable.NA.value == "-"
    assert Passable.IMP.value == "imp"


def test_edge_with_simple_passable():
    e = Edge(army=Passable.YES, fleet=Passable.NO, convoy_move=Passable.YES)
    assert e.army == Passable.YES


def test_edge_with_subfield_required_for_fleet():
    e = Edge(army=Passable.YES, fleet="SpN", convoy_move=Passable.YES)
    assert e.fleet == "SpN"


def test_map_ref_defaults_to_standard():
    r = MapRef()
    assert r.map_id == "standard"
    assert r.inline_map is None


def test_map_ref_accepts_inline():
    m = MapDefinition(fields={}, edges={})
    r = MapRef(inline_map=m)
    assert r.inline_map is m


def test_order_geo_info_moves():
    info = OrderGeoInfo(order_index=0, is_valid=True, effective_behavior="moves")
    assert info.is_valid is True
    assert info.effective_behavior == "moves"


def test_order_geo_info_invalid_mve_holds_no_support():
    info = OrderGeoInfo(
        order_index=2, is_valid=False,
        invalidity_code="GEO-003", invalidity_reason="not reachable",
        effective_behavior="holds_no_support",
    )
    assert info.effective_behavior == "holds_no_support"


def test_order_geo_info_invalid_sup_holds_supportable():
    info = OrderGeoInfo(
        order_index=1, is_valid=False,
        invalidity_code="GEO-004",
        effective_behavior="holds_supportable",
    )
    assert info.effective_behavior == "holds_supportable"


def test_order_geo_info_rejects_unknown_behavior():
    with pytest.raises(ValidationError):
        OrderGeoInfo(order_index=0, is_valid=True, effective_behavior="floats")


def test_convoy_graph_defaults_empty():
    g = ConvoyGraph()
    assert g.sea_edges == set()
    assert g.coastal_edges == set()
    assert g.convoyer_fields == set()
    assert g.cmove_candidates == set()
