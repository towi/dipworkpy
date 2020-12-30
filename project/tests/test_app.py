# 3rd pyrty
from fastapi.testclient import TestClient
# local
# under test
import dipworkpy


client = TestClient(dipworkpy.app)


def test_check_basic():
    response = client.post(
        "/check",
        json={"orders": [
            {'nation': "Au", "utype": "A", "current": "Vie", "order": "mve", "dest": "Mun"},
        ],
        }
    )
    assert response.status_code == 200
    json = response.json()
    assert sorted(json['nations']) == sorted(['Au'])
    assert sorted(json['utypes']) == sorted(['A'])
    assert sorted(json['afields']) == sorted(['Vie', 'Mun'])
    assert json['orders'] == {'con': 0, 'hld': 0, 'mve': 1, 'hsup': 0, 'msup': 0}
    #'order_errors': 0,


if __name__ == "__main__":
    import sys
    import pytest
    pytest.main(sys.argv)
