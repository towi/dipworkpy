"""Tests that the MapProtocol Protocol is correctly defined."""
from typing import get_type_hints

from dipworkpy.geography.map.protocol import MapProtocol


def test_protocol_has_required_methods():
    expected_methods = {
        "field_exists", "field_type", "superfield_of", "subfields_of",
        "is_supply_center", "home_center_of",
        "edge", "neighbors",
        "army_passable", "fleet_passable", "convoy_passable",
    }
    actual_methods = {m for m in dir(MapProtocol) if not m.startswith("_")}
    missing = expected_methods - actual_methods
    assert not missing, f"MapProtocol missing methods: {missing}"


def test_protocol_has_map_id_attribute():
    assert "map_id" in get_type_hints(MapProtocol)
