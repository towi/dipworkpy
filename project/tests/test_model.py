# 3rd pyrty
# local
# under test
import dipworkpy.model as model


def test_Order():
    result = model.Order(**{"nation": "Au", "utype": "A", "current": "Vie", "order": "mve", "dest": "Mun"})
    assert result.nation == "Au"
    assert result.utype == "A"
    assert result.current == "Vie"
    assert result.order == "mve"
    assert result.dest == "Mun"


def test_Situation():
    result = model.Situation(
        **{
            "orders": [
                {"nation": "Au", "utype": "A", "current": "Vie", "order": "mve", "dest": "Mun"},
            ],
            "switches": {
                "rule_interpretation_IX_3": 2,
            },
        }
    )
    assert len(result.orders) == 1


def test_switches_strict_unit_types_default_false():
    from dipworkpy.model import Switches
    assert Switches().strict_unit_types is False


def test_switches_strict_unit_types_can_be_enabled():
    from dipworkpy.model import Switches
    s = Switches(strict_unit_types=True)
    assert s.strict_unit_types is True


if __name__ == "__main__":
    import sys
    import pytest

    pytest.main(sys.argv)
