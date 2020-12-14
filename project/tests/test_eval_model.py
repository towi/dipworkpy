import dipworkpy.model as model
# under test
from dipworkpy.dip_eval.eval_model import t_world


def test_t_world_new():
    # arrange
    switches = model.Switches()
    # act
    world: t_world = t_world(
        fields_=set(),
        switches=switches,
    )
    # assert
    assert world


if __name__ == "__main__":
    import sys
    import pytest

    pytest.main(sys.argv)
