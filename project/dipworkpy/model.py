# std python
from enum import Enum
from typing import List, Dict, Set, Optional

# 3rd party
from pydantic import BaseModel, conint, constr, Field


########################
# common

class OrderType(str, Enum):
    """Note about 'hsup' and 'msup'. Because an order checking has
    to happen before the *Conflict Resulution* is done it is clear at the
    if a support order is a support-to-move or support-to-hold and must
    be distinguished in the input.

    Note too, that this is not the case or necessary for normal-move
    versus move-via-convoy ('nmove' vs. 'cmove'). From just looking at a
    single order one can not definitily say if a unit moves by land or ship.
    Therefore also move-by-convoys are given as 'mve'. If any other
    unit convoys this move, it is marged as 'cmove'. This might change
    the "power" of the move a tiny but (w.r.t. cutting supports?). Therefore
    a careful check of the geography has to be done before: Convoys that
    are not possible have to be changed to hold orders.
    """
    hld = "hld"
    mve = "mve"
    hsup = "hsup"  # support to hold
    msup = "msup"  # support to move
    con = "con"
    # patt = "patt"  # not a real order; only output; marking fields that are unavailable for retreats.


########################
# requests

class Order(BaseModel):
    nation: str
    utype: str = "A"
    current: str  # current field name
    order: Optional[OrderType] = None   # mve, hld, con, hsup. msup
    dest: Optional[str] = None  # target field of mve, con, hsup, msup; may be None if hld.
    def __log__(self):
        o = self.order  if self.order else ""
        d = self.dest  if self.dest else ""
        return f"{self.nation} {self.utype} {self.current} {o} {d}"


_ri_sc_ok = """
**self_cut_ok**

Ein Angriff einer Einheit auf eine unterstützende Einheit derselben Nation
verursacht bei Schalterstellung `True`, da`ss` dieser unterbrochen wird (siehe auch PARTIAL_CUT_POSSIBLE).
Beispiel:
- France: F MID-ENG; F Bre S F MID-ENG; A Pic-Bre
- England: F ENG xxx
In Schalterstellung `False` hat der Angriff der A Pic keine Wirkung auf die Unterstützung aus Bre,
folglich gelingt der Angriff und En F ENG würde vertrieben werden. Mit `True` erreicht man jedoch,
dass der Support aus Bre abgeschnitten wird, so daß der Angriff aus MID nicht stark genug ist,
um die F ENG zu vertreiben.
"""


_ri_9_3 = """
**rule_interpretation_IX_3**

Wenn ein Angreifer normalerweise den Konflikt gewinnt, aber die Einheit im Zielfeld
dieses nicht verläßt und die Nation der Einheit im Zielfeld den Angreifer unterstützt hat, dann gelingt
die Bewegung des An¬greifers nur wenn:
- 0: Auch bei Nichtberücksichtigung der Unterstützungen der Nation der Ein¬heit im Zielfeld
     für alle Angreifer, diese vertrieben werden würde.
- 1: Auch bei Nichtberücksichtigung der Unterstützungen der Nation der Einheit im Zielfeld für alle Angreifer,
     derselbe Angreifer den Kon¬flikt gewinnen würde.
- 2: Dieser Angriff auch ohne die Unterstützungen der Nation der Einheit im Zielfeld stärker
     als die Verteidigungsstärke des Zielfeldes ist.
Im obenstehenden Beispiel ((TODO)) bewegte sich die En F ENG nicht. Die Fr F MID gewinnt
den Konflikt in ENG zunächst. Nach Regel IX.3. zählen die Unterstützungen des Engländers zu dem Angriff
jedoch nicht bei einer Vertreibung, werden also in einem zweiten Auswertungsschritt ignoriert.
Das hat jedoch zur Folge, dass die Ge F Bel den Konflikt in ENG gewinnen würde.
Bei Schalterstellung "0" gelingt Fr F MID-ENG, weil "En F ENG trotzdem vertrieben wird".
Bei Schalterstellung "1" gelingt weder Fr F MID-ENG noch Ge F Bel-ENG,
weil "nicht derselbe Angreifer den Konflikt gewinnt".
Bei Schalterstel¬lung "2" gelingt auch keine der Bewegungen: Es wird ohnehin
nur Fr F MID-ENG betrachtet und die kann ohne die engli¬schen Unterstützungen nicht vertreiben.
"""

class Switches(BaseModel):
    verbose: Optional[bool] = False
    self_cut_ok: Optional[bool] = Field(default=False, description=_ri_sc_ok)
    rule_interpretation_IX_3: Optional[int] = Field(default=0, ge=0, le=2, description=_ri_9_3) # 0,1,2
    rule_interpretation_IX_7: Optional[int] = 0 # 0,1,2
    convoy_cuts: Optional[bool] = False
    partial_cut_possible: Optional[int] = 0 # Not used for single-strengh-variant
    #
    convoy_routing_engine: Optional[str] = "always"


# TODO: "overfields" have to be implemented somehow. But:
#   W.r.t. conflict resolution subfields are completly irrelevant.
#   Therefore the input to the conflict dip_eval will probably have to be
#   free of any sobfields anyway. Thus "SpN" must be given as "Spa" etc.
#   It might be that the input 'Situation' will be cleaned w.r.t to geography
#   internally before conflict resolution later. But the conflict resolver will
#   probably always work if all subfield/overfield-resolution has taken place already.
#   As far as I know there is never a difference in the conflict resolution phase
#   with the additional knowlesge that a unit is in a specific subfield or
#   if computed entirely on overfields.
class Situation(BaseModel):
    orders: List[Order] = []
    switches: Optional[Switches] = Switches()


########################
# results

def _decode_optional_bool(value: Optional[bool], on_true, on_false, on_none):
    if value is None: return on_none
    if value: return on_true
    return on_false


class OrderResult(BaseModel): # could be derived from Order?
    nation: str
    utype: str = "A"  # TODO
    current: str  # current field name
    order: OrderType = None   # mve, hld, con, sup
    dest: Optional[str] = None  # target field of mve, con, sup; may be None on hld
    succeeds: Optional[bool] = True  # for results
    dislodged: Optional[bool] = False  # for results. retreat or disband
    original : Optional[Order] = None  # may be None in tests, but usually set

    def __log__(self):
        s = _decode_optional_bool(self.succeeds, on_true="!!", on_false=" !", on_none="")
        d = _decode_optional_bool(self.dislodged, on_true=" >", on_false=">>", on_none="")
        o = self.order  if self.order else ""
        t = self.dest  if self.dest else ""
        orig = " (" + self.original.__log__() + ")"  if self.original else ""
        return f"'{self.nation} {self.utype} {self.current} {o} {t} {s}{d}{orig}'"

    def __le__(self, other):
        """Like == but skips 'original'; Example: test_conflict_game_02.
        Not a pretty solution, but it allows the use of '<=' in assertions and keeping all information
        for analysis. But in general its better to use clear_originals() before ==."""
        # skip comparing 'original'
        for n,v in self.__fields__.items():
            if n=="original": continue
            sv = self.__getattribute__(n)
            ov = other.__getattribute__(n)
            if sv is None and ov is None: continue  # both are None
            if sv is None or ov is None: return False  # only one is None
            if sv <= ov: continue
            return False
        return True


class ConflictResolution(BaseModel):
    orders: List[OrderResult]
    pattfields: Optional[Set[str]]  # fields unavailable for retreats

    def __log__(self):
        return ", ".join([ o.__log__()  for o in self.orders]) + "; " + str(self.pattfields)

    def __le__(self, other):
        """Not a pretty solution, but it allows the use of '<=' in assertions and keeping all information
        for analysis. But in general its better to use clear_originals() before ==. Example: test_conflict_game_02"""
        return self.orders<=other.orders and self.pattfields==other.pattfields

    def clear_originals(self):
        """Sets all original orders to None to allow assertions with ==.
        The disadvantage is that you losose information for analysis; if you
        want that information use the '<=' operator. Example: test_conflict_game_02"""
        for o in self.orders:
            o.original = None
        return self

    def show(self, f, line_prefix=""):
        print(f"{line_prefix}Orders", file=f)
        for o in self.orders:
            print(f"{line_prefix}-", o, file=f)
        print(f"{line_prefix}Pattfields", file=f)
        print(f"{line_prefix}:", " ".join(sorted(self.pattfields)), file=f)


class ConflictCheck(BaseModel):
    nations: Set[str]
    utypes: Set[str]
    afields: Set[str]
    orders: Dict[OrderType, int]  # {'hld' : ..., }
    order_errors = int

########################
