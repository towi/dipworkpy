from dipworkpy.conflict.model import ConflictRequest, ConflictResponse
from dipworkpy.model import Order, OrderType


def test_conflict_request_minimal():
    req = ConflictRequest(orders=[
        Order(nation="Au", utype="A", current="Vie", order=OrderType.hld),
    ])
    assert req.order_geo_info is None
    assert req.convoy_graph is None


def test_conflict_response_default_diagnostics():
    from dipworkpy.model import ConflictResolution
    resp = ConflictResponse(resolution=ConflictResolution(orders=[], pattfields=set()))
    assert resp.diagnostics == []
