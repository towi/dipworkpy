from dipworkpy.geography.model import GeographyRequest, GeographyResponse
from dipworkpy.model import Order, OrderType


def test_geography_request_defaults():
    req = GeographyRequest(orders=[])
    assert req.map.map_id == "standard"


def test_geography_request_with_orders():
    orders = [Order(nation="Au", utype="A", current="Vie", order=OrderType.hld)]
    req = GeographyRequest(orders=orders)
    assert len(req.orders) == 1


def test_geography_response_default_empty():
    resp = GeographyResponse(orders=[], order_geo_info=[])
    assert resp.convoy_graph.sea_edges == set()
    assert resp.diagnostics == []
