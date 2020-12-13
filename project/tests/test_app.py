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
            {'nation': "Au", "utype": "A", "current": "Vie", "order": "mve", "target": "Mun"},
        ],
        }
    )
    assert response.status_code == 200
    assert response.json() == {
        'nations': ['Au'],
        'utypes': ['A'],
        'afields': ['Vie', 'Mun'],
        'orders': {'con': 0, 'hld': 0, 'mve': 1, 'sup': 0},
        #'order_errors': 0,
    }


if __name__ == "__main__":
    import sys
    import pytest
    pytest.main(sys.argv)
