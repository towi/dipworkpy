# std lib
import logging
# local
from dipworkpy.model import Situation, Order, OrderType, ConflictResolution, OrderResult, Switches
# under test
from dipworkpy.conflict_game import conflict_game

import pytest
import json


def pytest_generate_tests(metafunc):
    # called once per each test function
    funcarglist = metafunc.cls.params[metafunc.function.__name__]
    argnames = sorted(funcarglist[0])
    metafunc.parametrize(
        argnames, [[funcargs[name] for name in argnames] for funcargs in funcarglist]
    )


def _read_testdata(fn):
    with open(fn) as fin:
        return json.load(fin)


class TestClass:
    # a map specifying multiple argument sets for a test method
    params = {
        "test_testdata": _read_testdata("testdata.json"),
    }

    def test_testdata(self, id, orders, order_results, pattfields):
        # arrange
        situation: Situation = Situation(orders=orders)
        # act
        result = conflict_game(situation)
        # assert
        expected = ConflictResolution(orders=order_results, pattfields=pattfields)
        # '<=' ignores 'original'
        assert result <= expected, f"\nres: {result.__log__()} !=\nexp: {expected.__log__()}"


################################################


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        # format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        format='%(filename)s:%(lineno)d: [%(levelname)s] %(funcName)s | %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S'
    )
    import sys
    import pytest
    pytest.main(sys.argv + ['-vv'])
