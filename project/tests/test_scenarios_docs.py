# std py
import re
# 3rdparly
import lrparsing
# local
from dipworkpy.model import Situation, Order
# under test
from dipworkpy.conflict_game import conflict_game

class POrder():
    def __init__(self, unit, ffield, order, nation=None, dnation=None, dfield=None, dorder=None, ddfield=None):
        self.nation = nation
        self.order = order
        self.unit = unit
        self.ffield = ffield
        self.dnation = dnation
        self.dunit = dunit
        self.dfield = dfield
        self.dorder = dorder
        self.ddfield = ddfield


class DippyStandardOrder:
    re_toks = re.compile(r"(\W+)")
    def __init__(self):
        pass

    def parse(self, s):
        toks = self.re_toks.split(s)
        toks = [ t.strip()  for t in toks ]
        toks = [ t  for t in toks  if t ]
        print(" -", s, "=", toks)
        if len(toks) == 2:
            return

############################################


if __name__ == "__main__":
    for s in ["A Bur-Par", "Au A Bur - Par", "Au F NTH xxx", "Au F NTH-xxx",
              "F Bur", "Au F Bur",
              "Au A Tri S A Mun-Vie",
              "Au A Tri S A Mun xxx", "Au A Tri S A Mun-xxx", "Au A Tri S A Mun",
              "A Tri S A Mun xxx", "A Tri S A Mun-xxx", "A Tri S A Mun"
              ]:
        parser = DippyStandardOrder()
        parser.parse(s)
    #
    #import pytest
    #pytest.main(sys.argv)
