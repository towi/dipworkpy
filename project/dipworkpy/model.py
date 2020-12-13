# std python
from enum import Enum
from typing import List, Dict, Set, Optional

# 3rd party
from pydantic import BaseModel, conint, constr, Field


########################
# common

class OrderType(str, Enum):
    hld = "hld"
    mve = "mve"
    sup = "sup"
    con = "con"

########################
# requests

class Order(BaseModel):
    nation: str
    utype: str = "A"
    current: str  # current field name
    order: Optional[OrderType] = None   # mve, hld, con, sup
    target: Optional[str] = None  # target field of mve, con, sup


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
#   Therefore the input to the conflict cfl_resolve will probably have to be
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

class OrderResult(BaseModel): # could be derived from Order?
    nation: str
    utype: str = "A"
    current: str  # current field name
    order: Optional[OrderType] = None   # mve, hld, con, sup
    target: Optional[str] = None  # target field of mve, con, sup
    success: Optional[bool] # for results
    dislodged: Optional[bool] # for results. retreat or disband


class ConflictResolution(BaseModel):
    orders: List[OrderResult]


class ConflictCheck(BaseModel):
    nations: Set[str]
    utypes: Set[str]
    afields: Set[str]
    orders: Dict[OrderType, int]  # {'hld' : ..., }
    order_errors = int

########################
