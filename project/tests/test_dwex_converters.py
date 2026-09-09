from dipworkpy.tools.dwex.lang import parse
from dipworkpy.tools.dwex.to_situation import to_situation, to_expected
from dipworkpy.tools.dwex.to_map import to_inline_map
from dipworkpy.model import OrderType

DOC = """
@dwex
title: t
map {
  Vie LA 0,0
  Mun LA 1,0
  Tyr L  0,1
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


def test_to_situation_produces_orders():
    doc = parse(DOC)
    sit = to_situation(doc)
    assert len(sit.orders) == 2
    assert sit.orders[0].nation == "Au"
    assert sit.orders[0].order == OrderType.mve
    assert sit.orders[0].dest == "Tyr"


def test_to_expected_marks_failures():
    doc = parse(DOC)
    exp = to_expected(doc)
    assert all(r.succeeds is False for r in exp.orders)


def test_to_inline_map_has_three_fields():
    doc = parse(DOC)
    m = to_inline_map(doc)
    assert m.field_exists("Vie")
    assert m.field_exists("Mun")
    assert m.field_exists("Tyr")


def test_to_inline_map_has_six_directed_edges():
    doc = parse(DOC)
    m = to_inline_map(doc)
    # 3 undirected edges -> 6 directed
    assert m.edge("Vie", "Mun") is not None
    assert m.edge("Mun", "Vie") is not None
    assert m.edge("Vie", "Tyr") is not None
    assert m.edge("Tyr", "Vie") is not None
