from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType


def test_geography_phase_classifies_orders():
    req = GeographyRequest(orders=[
        Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh"),
        Order(nation="Au", utype="A", current="Bud", order=OrderType.mve, dest="ZZZ"),
    ])
    resp = geography_phase(req)
    assert len(resp.order_geo_info) == 2
    assert resp.order_geo_info[0].is_valid is True
    assert resp.order_geo_info[1].is_valid is False
    assert resp.order_geo_info[1].invalidity_code == "GEO-001"


def test_geography_phase_emits_diagnostics():
    req = GeographyRequest(orders=[
        Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh"),
    ])
    resp = geography_phase(req)
    # at minimum one diagnostic per order
    assert len(resp.diagnostics) >= 1


def test_geography_phase_normalizes_subfields_in_output():
    req = GeographyRequest(orders=[
        Order(nation="Fr", utype="F", current="SpN", order=OrderType.hld),
    ])
    resp = geography_phase(req)
    assert resp.orders[0].current == "Spa"
    assert resp.order_geo_info[0].resolved_coast == "SpN"
