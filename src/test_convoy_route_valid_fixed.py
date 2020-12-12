# local
from impl_resolve import t_field, t_order

# under test
from impl_resolve import _convoy_route_valid_fixed as route


def mk_field(name, dest):
    return t_field(
        player="Au",
        order = t_order.cmove,
        dest=dest,
        xref=dest,
        strength=1,
        name=name,
        original_order = None)


def test_simple_ok():
    # arrange
    field = mk_field(name="Lon", dest="Kie")
    edges = {("Lon", "NTH"), ("NTH", "Kie")}
    # act
    result = route(field, edges, {"NTH"})
    # assert
    assert result
    assert field._events[-1] == "$cnv:['Lon', 'NTH', 'Kie']"


def test_simple_fail():
    # arrange
    field = mk_field(name="Lon", dest="Kie")
    edges = {("Lon", "NTH"), ("NTH", "Kie")}
    # act
    result = route(field, edges, {"MED"})  # <<< no convoyers
    # assert
    assert not result


if __name__ == "__main__":
    import sys
    import pytest

    pytest.main(sys.argv)
