"""
Taken in big chunks from DIP_EVAL.pas.
"""

from .eval_k1 import k1_evaluation
from .eval_k2 import k2_evaluation
from .eval_k3 import k3_evaluation
from .eval_k4 import k4_evaluation
from .eval_k0 import k0_evaluation

class LogList:
    def __init__(self, items, prefix="\n- ", suffix="", join="", begin="", end=""):
        self.items = items
        self.prefix = prefix
        self.suffix = suffix
        self.join = join
        self.begin = begin
        self.end = end
    def __str__(self):
        res = [ self.begin ]
        for item in self.items:
            if hasattr(item, "__log__"):
                s = item.__log__()
            else:
                s = str(item)
            res.append(self.prefix + s + self.suffix)
        res.append(self.end)
        return self.join.join(res)

