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


def _support_doc(order_line: str):
    return f"""
@dwex
title: t
map {{
  Mun L 0,0
  Ber L 1,1
  Kie L 2,0
  Mun -- Ber
  Ber -- Kie
}}
orders {{
  Ge A Ber mve Kie
  {order_line}
}}
@end
"""


def test_msup_implicit_notation_has_no_target():
    doc = parse(_support_doc("Ge A Mun msup Ber"))
    msup = next(o for o in doc.orders if o.order == "msup")
    assert msup.dest == "Ber"
    assert msup.target is None


def test_msup_explicit_sup_mve():
    doc = parse(_support_doc("Ge A Mun sup Ber mve Kie"))
    msup = next(o for o in doc.orders if o.order == "msup")
    assert msup.dest == "Ber"
    assert msup.target == "Kie"


def test_msup_explicit_msup_dash():
    doc = parse(_support_doc("Ge A Mun msup Ber - Kie"))
    msup = next(o for o in doc.orders if o.order == "msup")
    assert msup.dest == "Ber"
    assert msup.target == "Kie"


def test_msup_explicit_with_unit_prefix_a():
    doc = parse(_support_doc("Ge A Mun sup A Ber mve Kie"))
    msup = next(o for o in doc.orders if o.order == "msup")
    assert msup.dest == "Ber"
    assert msup.target == "Kie"


def test_msup_explicit_with_unit_prefix_nation_and_utype():
    doc = parse(_support_doc("Ge A Mun sup Ge A Ber mve Kie"))
    msup = next(o for o in doc.orders if o.order == "msup")
    assert msup.dest == "Ber"
    assert msup.target == "Kie"


def test_msup_explicit_survives_failure_marker():
    doc = parse(_support_doc("Ge A Mun sup Ber mve Kie !"))
    msup = next(o for o in doc.orders if o.order == "msup")
    assert msup.target == "Kie"
    assert msup.expected_failed is True


def test_cmve_order_keyword():
    doc = parse(
        """
@dwex
title: cmve keyword
map {
  Con LA 0,0
  Bul LA 1,0
  BLA O 0.5,0.8
  Con -- Bul
  Con --F BLA
  BLA --F Bul
}
orders {
  Tu A Con cmve Bul
  Tu F BLA con Con
}
@end
"""
    )
    assert doc.orders[0].order == "cmve"
    assert doc.orders[0].dest == "Bul"
    assert doc.orders[1].order == "con"


def test_switches_block():
    doc = parse(
        """
@dwex
title: switches
map {
  Con LA 0,0
  Bul LA 1,0
  Con -- Bul
}
orders {
  Tu A Con mve Bul via !
}
switches {
  convoy_via_explicit
}
@end
"""
    )
    assert doc.switches == {"convoy_via_explicit": True}
    doc2 = parse(
        """
@dwex
title: switches
map {
  Con LA 0,0
  Bul LA 1,0
  Con -- Bul
}
orders {
  Tu A Con mve Bul !
}
switches {
  convoy_via_explicit false
}
@end
"""
    )
    assert doc2.switches == {"convoy_via_explicit": False}


def test_switches_block_rejects_unknown_switch():
    with pytest.raises(DwexParseError):
        parse(
            """
@dwex
title: bad
map {
  Con LA 0,0
}
orders {
  Tu A Con hld
}
switches {
  no_such_switch
}
@end
"""
        )
