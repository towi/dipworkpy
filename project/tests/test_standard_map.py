"""Tests for StandardMap - the bundled FIELDS-shape map loader."""
import pytest

from dipworkpy.geo_model import FieldType
from dipworkpy.geography.map.standard import StandardMap


@pytest.fixture(scope="module")
def m():
    return StandardMap()


def test_field_exists_known(m):
    assert m.field_exists("Vie")
    assert m.field_exists("NTH")


def test_field_exists_unknown(m):
    assert not m.field_exists("ZZZ")


def test_field_type(m):
    assert m.field_type("Vie") == FieldType.LA
    assert m.field_type("NTH") == FieldType.O
    assert m.field_type("Spa") == FieldType.LC


def test_superfield_self_for_non_subfield(m):
    assert m.superfield_of("Vie") == "Vie"
    assert m.superfield_of("Spa") == "Spa"


def test_superfield_for_subfield(m):
    assert m.superfield_of("SpN") == "Spa"
    assert m.superfield_of("SpS") == "Spa"


def test_subfields_of_split_coast(m):
    assert set(m.subfields_of("Spa")) == {"SpN", "SpS"}
    assert set(m.subfields_of("Pet")) == {"PeN", "PeS"}


def test_subfields_of_non_split(m):
    assert m.subfields_of("Vie") == []


def test_neighbors(m):
    nbrs = m.neighbors("Vie")
    assert "Boh" in nbrs
    assert "Bud" in nbrs
    assert "Tyr" in nbrs


def test_edge_returns_none_for_non_adjacent(m):
    assert m.edge("Vie", "Lon") is None


def test_army_passable_basic(m):
    assert m.army_passable("Vie", "Boh") is True
    assert m.army_passable("Vie", "NTH") is False


def test_supply_center_flag(m):
    assert m.is_supply_center("Vie") is True
    assert m.is_supply_center("Boh") is False
