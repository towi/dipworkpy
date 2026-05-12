import pytest

from dipworkpy.geography.map.registry import get_map, list_maps, register_map


def test_get_standard_map():
    m = get_map("standard")
    assert m.map_id == "standard"
    assert m.field_exists("Vie")


def test_unknown_map_raises():
    with pytest.raises(KeyError):
        get_map("nonsuch")


def test_list_maps_contains_standard():
    assert "standard" in list_maps()


def test_register_custom_map():
    from dipworkpy.geo_model import MapDefinition
    from dipworkpy.geography.map.inline import InlineMap
    custom = InlineMap(MapDefinition(), map_id="empty_test")
    register_map(custom)
    assert "empty_test" in list_maps()
    assert get_map("empty_test").map_id == "empty_test"
