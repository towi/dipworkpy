from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType


def test_geography_phase_classifies_orders():
    req = GeographyRequest(
        orders=[
            Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh"),
            Order(nation="Au", utype="A", current="Bud", order=OrderType.mve, dest="ZZZ"),
        ]
    )
    resp = geography_phase(req)
    assert len(resp.order_geo_info) == 2
    assert resp.order_geo_info[0].is_valid is True
    assert resp.order_geo_info[1].is_valid is False
    assert resp.order_geo_info[1].invalidity_code == "GEO-001"


def test_geography_phase_emits_diagnostics():
    req = GeographyRequest(
        orders=[
            Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh"),
        ]
    )
    resp = geography_phase(req)
    # at minimum one diagnostic per order
    assert len(resp.diagnostics) >= 1


def test_geography_phase_normalizes_subfields_in_output():
    req = GeographyRequest(
        orders=[
            Order(nation="Fr", utype="F", current="SpN", order=OrderType.hld),
        ]
    )
    resp = geography_phase(req)
    assert resp.orders[0].current == "Spa"
    assert resp.order_geo_info[0].resolved_coast == "SpN"
    # GEO-007 should be emitted because we recorded the coast
    assert any(d.rule == "GEO-007" for d in resp.diagnostics)
    # GEO-008 should be emitted because the on-the-wire form was rewritten
    assert any(d.rule == "GEO-008" for d in resp.diagnostics)


def test_geography_phase_resolves_coast_for_fleet_move():
    # F Spa mve LYO — LYO is reachable only from the south coast,
    # so coast resolution should produce SpS and emit GEO-007.
    req = GeographyRequest(
        orders=[
            Order(nation="Fr", utype="F", current="Spa", order=OrderType.mve, dest="LYO"),
        ]
    )
    resp = geography_phase(req)
    assert resp.order_geo_info[0].resolved_coast == "SpS"
    assert any(d.rule == "GEO-007" for d in resp.diagnostics)
    # In this case `current` was already "Spa" (super), so GEO-008 should NOT fire
    assert not any(d.rule == "GEO-008" for d in resp.diagnostics)


def test_geography_phase_accepts_multi_sea_convoy_route():
    req = GeographyRequest(
        orders=[
            Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="Bre"),
            Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Lon"),
            Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Lon"),
        ]
    )
    resp = geography_phase(req)
    assert resp.order_geo_info[0].is_convoy_move is True
    assert resp.order_geo_info[0].is_valid is True
    assert resp.order_geo_info[1].is_valid is True
    assert resp.order_geo_info[2].is_valid is True


def test_geography_phase_rejects_unconnected_convoy_order():
    req = GeographyRequest(
        orders=[
            Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="Bel"),
            Order(nation="It", utype="F", current="ION", order=OrderType.con, dest="Lon"),
        ]
    )
    resp = geography_phase(req)
    assert resp.order_geo_info[0].is_convoy_move is False
    assert resp.order_geo_info[1].is_valid is False
    assert resp.order_geo_info[1].invalidity_code == "GEO-006"


def test_geography_phase_rejects_convoyer_not_on_selected_route():
    req = GeographyRequest(
        orders=[
            Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="Bel"),
            Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Lon"),
            Order(nation="It", utype="F", current="ION", order=OrderType.con, dest="Lon"),
        ]
    )
    resp = geography_phase(req)
    assert resp.order_geo_info[0].is_convoy_move is True
    assert resp.order_geo_info[1].is_valid is True
    assert resp.order_geo_info[2].is_valid is False
    assert resp.order_geo_info[2].invalidity_code == "GEO-006"
