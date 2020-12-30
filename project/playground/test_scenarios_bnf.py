"""
A try with a "simple" BNF grammar parser.
Cool, but unfinished.
"""

# 3rdparly
import lrparsing
# local
from dipworkpy.model import Situation, Order
# under test
from dipworkpy.conflict_game import conflict_game


class DippyStandardOrder(lrparsing.Grammar):
    """
Field = 'Abc' | 'ABC'
Unit = 'A ' | 'F '
Nation = 'Au ' | 'En ' | 'Fr ' | 'Ge ' | 'It ' | 'Ru ' | 'Tu '
Location = [Nation] Unit Field
SupportableOrder = MoveOrder | HoldOrder
ConvoyableOrder = MoveOrder
SupportOrder = ' S ' Location SupportableOrder | ' S "'
ConvoyOrder = ' C ' Location ConvoyableOrder
HoldOrder = ' xxx' | '-xxx'
MoveOrder = '-' Field
AnyOrder = MoveOrder | HoldOrder | ConvoyOrder | SupportOrder
Scanline = Location AnyOrder
    """
    Field = lrparsing.Token(re=r'[A-Z][A-Za-z][A-Za-z]')

    Unit = lrparsing.Token(re=r'[A-Z] ')

    Nation = lrparsing.Token(re=r'[A-Z][a-z] ')

    Location = Nation + Unit + Field |  Unit + Field

    HoldOrder = lrparsing.Choice(' xxx', '-xxx')
    MoveOrder = '-' + Field
    SupportableOrder = MoveOrder | HoldOrder
    ConvoyableOrder = MoveOrder *1
    SupportOrder = ' S ' + Location + SupportableOrder | ' S "'
    ConvoyOrder = ' C ' + Location + ConvoyableOrder

    AnyOrder = AnyOrder = MoveOrder | HoldOrder | ConvoyOrder | SupportOrder
    Scanline = Location + AnyOrder

    START = Scanline                      # Where the grammar must start
    COMMENTS = (                      # Allow C and Python comments
        lrparsing.Token(re="#(?:[^rn]*(?:rn?|nr?))") |
        lrparsing.Token(re="/[*](?:[^*]|[*][^/])*[*]/"))


############################################

def tree_factory(tpl):
    # ... code here... ?
    return tpl


if __name__ == "__main__":
    # Das klappt zwar ganz toll, aber mir ist nicht klar, wie ich den parse_tree
    # auf einfache Weise so "zerlege", dass ich an die Elemete des Zuges drankomme.
    import sys
    parse_tree = DippyStandardOrder.parse("A Bre-Par", tree_factory=tree_factory)
    print(DippyStandardOrder.repr_parse_tree(parse_tree), file=sys.stderr)
    #
    #import pytest
    #pytest.main(sys.argv)
