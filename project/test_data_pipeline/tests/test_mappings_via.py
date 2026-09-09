"""GEO-010: DipNet "VIA" (move via convoy) maps to Order.via_convoy."""

from dipworkpy.model import Order, OrderType

from test_data_pipeline.mappings import parse_dipnet_order


def test_plain_move_has_no_via():
    o = parse_dipnet_order("A VIE - BUD", "Au")
    assert o.via_convoy is False


def test_via_move_sets_flag():
    o = parse_dipnet_order("A VIE - BUD VIA", "Au")
    assert o.via_convoy is True
    assert o.order == OrderType.mve and o.dest == "Bud"


def test_via_with_coast_suffix():
    o = parse_dipnet_order("F STP/NC - BAR VIA", "Ru")
    assert o.via_convoy is True


def test_order_default_no_via():
    # pydantic default: no migration needed
    assert Order(nation="Au", utype="A", current="Vie").via_convoy is False
