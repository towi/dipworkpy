import pytest
from dipworkpy.tools.dwex.lang import parse, DwexParseError

EXAMPLE = """
@dwex
title: Two armies bouncing
desc: Equal strength bounce.

map {
  Vie LA 0,0
  Mun LA 2,0
  Tyr L  1,1
  Vie -- Mun
  Vie -- Tyr
  Mun -- Tyr
}

orders {
  Au A Vie mve Tyr !
  Ge A Mun mve Tyr !
}
@end
"""


def test_parses_title():
    doc = parse(EXAMPLE)
    assert doc.title == "Two armies bouncing"


def test_parses_description():
    doc = parse(EXAMPLE)
    assert "Equal" in doc.description


def test_parses_three_fields():
    doc = parse(EXAMPLE)
    names = {f.name for f in doc.fields}
    assert names == {"Vie", "Mun", "Tyr"}


def test_parses_field_positions():
    doc = parse(EXAMPLE)
    vie = next(f for f in doc.fields if f.name == "Vie")
    assert vie.x == 0.0
    assert vie.y == 0.0
    assert vie.type == "LA"


def test_parses_three_undirected_edges():
    doc = parse(EXAMPLE)
    pairs = {tuple(sorted([e.a, e.b])) for e in doc.edges}
    assert pairs == {("Mun", "Vie"), ("Tyr", "Vie"), ("Mun", "Tyr")}


def test_parses_orders_with_failure_marker():
    doc = parse(EXAMPLE)
    assert len(doc.orders) == 2
    for o in doc.orders:
        assert o.expected_failed is True


def test_extracts_units_from_orders():
    doc = parse(EXAMPLE)
    nations = {u.nation for u in doc.units}
    assert nations == {"Au", "Ge"}


def test_rejects_missing_dwex_marker():
    with pytest.raises(DwexParseError):
        parse("title: missing markers\nmap {}\norders {}")


def test_edge_modifier_army_only():
    text = """
@dwex
title: t
map {
  A LA 0,0
  B LA 1,0
  A --A B
}
@end
"""
    doc = parse(text)
    e = doc.edges[0]
    assert e.army == "ja"
    assert e.fleet == "nein"


def test_edge_modifier_fleet_only():
    text = """
@dwex
title: t
map {
  A O 0,0
  B O 1,0
  A --F B
}
@end
"""
    doc = parse(text)
    e = doc.edges[0]
    assert e.fleet == "ja"
    assert e.army == "nein"
