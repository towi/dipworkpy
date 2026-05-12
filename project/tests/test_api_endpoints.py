from fastapi.testclient import TestClient

from dipworkpy.api_app import app

client = TestClient(app)


def test_syntax_endpoint():
    r = client.post("/syntax/", json={
        "orders": [],
        "unit_positions": {"Vie": ["Au", "A"]},
    })
    assert r.status_code == 200
    body = r.json()
    assert any(d["rule"] == "SYN-008" for d in body["diagnostics"])


def test_geography_endpoint():
    r = client.post("/geography/", json={
        "orders": [{"nation": "Au", "utype": "A", "current": "Vie",
                    "order": "mve", "dest": "Boh"}],
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["order_geo_info"]) == 1
    assert body["order_geo_info"][0]["is_valid"] is True


def test_round_endpoint_end_to_end():
    r = client.post("/round/", json={
        "orders": [{"nation": "Au", "utype": "A", "current": "Vie",
                    "order": "mve", "dest": "Boh"}],
        "unit_positions": {"Vie": ["Au", "A"]},
    })
    assert r.status_code == 200
