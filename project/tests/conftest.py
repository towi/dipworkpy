from itertools import zip_longest

from dipworkpy.model import Situation, Order, OrderType, ConflictResolution, OrderResult
from dipworkpy.conflict_game import t_field

#

def _op_ConflictResolution(op, left : ConflictResolution, right : ConflictResolution):
    if False:
        import pprint
        ls = pprint.pformat(left.json(), 2, 240).splitlines()
        rs = pprint.pformat(right.json(), 2, 240).splitlines()
        return ["Comparing ConflictResolution instances:"] + ["LEFT:"] + ls + ["RIGHT:"] + rs
    elif False:
        res = ["Comparing ConflictResolution instances: " + op]
        res.append("ORDERS:")
        for lo, ro in zip_longest(left.orders, right.orders, fillvalue=None):
            if lo != ro:
                res.append(f"!!! {lo} != {ro}")
            else:
                res.append(f"== {lo} == {ro}")
        res.append(f"PATTFIELDS: {left.pattfields} =?= {right.pattfields}")
        return res
    return [ "left " + op + " right:", left.__log__(), right.__log__() ]


def _op_model(op, model_type, model_name, left, right):
    res = [f"- {left}", f"- {right}"]
    diffs = []
    for f in model_type.__fields__:
        vl, vr = left.__getattribute__(f), right.__getattribute__(f)
        if vl != vr:
            res.append(f"!!! {f}: {vl} != {vr}")
            diffs.append(f)
    return [f"Showing {model_name} {op} <" + ",".join(diffs)+">"] + res


def _op_t_field(op, left : t_field, right : t_field):
    return _op_model(op, t_field, "t_field", left, right)


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, ConflictResolution) and isinstance(right, ConflictResolution):
        return _op_ConflictResolution(op, left, right)
    elif isinstance(left, t_field) and isinstance(right, t_field):
        return _op_t_field(op, left, right)
