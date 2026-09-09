# std python
from enum import Enum
from typing import List, Dict, Set, Optional

# 3rd party
from pydantic import BaseModel, Field


########################
# common


class OrderType(str, Enum):
    """Note about 'hsup' and 'msup'. Because an order checking has
    to happen before the *Conflict Resulution* is done it is clear at the
    if a support order is a support-to-move or support-to-hold and must
    be distinguished in the input.

    Note too, that this is not the case or necessary for normal-move
    versus move-via-convoy ('nmove' vs. 'cmove'). From just looking at a
    single order one can not definitely say if a unit moves by land or ship.
    Therefore, also move-by-convoys are given as 'mve'. If any other
    unit convoys this move, it is marked as 'cmove'. This might change
    the "power" of the move a tiny but (w.r.t. cutting supports?). Therefore,
    a careful check of the geography has to be done before: Convoys that
    are not possible have to be changed to hold orders.
    """

    hld = "hld"
    mve = "mve"
    hsup = "hsup"  # support to hold
    msup = "msup"  # support to move
    con = "con"
    # This moved to ConflictResults.pattfields in the python implementation:
    # patt = "patt"  # not a real order; only output; marking fields that are unavailable for retreats.


########################
# requests


class Order(BaseModel):
    nation: str
    utype: str = "A"
    current: str  # current field name
    order: Optional[OrderType] = None  # mve, hld, con, hsup. msup
    dest: Optional[str] = None  # target field of mve, con, hsup, msup; may be None if hld.
    via_convoy: bool = False  # GEO-010 / Gilgamesch B.3.2.14: explicit "mve [Convoy]"

    def __log__(self):
        o = self.order if self.order else ""
        d = self.dest if self.dest else ""
        via = " [Convoy]" if self.via_convoy else ""
        return f"{self.nation} {self.utype} {self.current} {o} {d}{via}"


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
Im Gilgamesch-Beispiel (Fr F MID-ENG; En F NTH/Lon S Fr F MID-ENG; Ge F Bel-ENG;
Ge F Bre S Ge F Bel-ENG; En F ENG hält) bewegte sich die En F ENG nicht. Die Fr F MID gewinnt
den Konflikt in ENG zunächst. Nach Regel IX.3. zählen die Unterstützungen des Engländers zu dem Angriff
jedoch nicht bei einer Vertreibung, werden also in einem zweiten Auswertungsschritt ignoriert.
Das hat jedoch zur Folge, dass die Ge F Bel den Konflikt in ENG gewinnen würde.
Bei Schalterstellung "0" gelingt Fr F MID-ENG, weil "En F ENG trotzdem vertrieben wird".
Bei Schalterstellung "1" gelingt weder Fr F MID-ENG noch Ge F Bel-ENG,
weil "nicht derselbe Angreifer den Konflikt gewinnt".
Bei Schalterstel¬lung "2" gelingt auch keine der Bewegungen: Es wird ohnehin
nur Fr F MID-ENG betrachtet und die kann ohne die engli¬schen Unterstützungen nicht vertreiben.

DATC-Zuordnung (v3.2; verifiziert gegen testdata/datc-v3/DATC_v3_2.html):
- 6.D.12 "SUPPORTING A FOREIGN UNIT TO DISLODGE OWN UNIT PROHIBITED" und 6.D.13
  (idem für rückkehrende eigene Einheit): Unterstützungen der Nation der Einheit im
  Zielfeld sind für die Vertreibung der eigenen Einheit wirkungslos -- das ist die
  strength_b-Behandlung in eval_common.count_supporters (gilt für alle drei Werte).
- 6.E.12 "SUPPORT ON ATTACK ON OWN UNIT CAN BE USED FOR OTHER MEANS": die wirkungslose
  Unterstützung zählt dennoch im Stärkevergleich der Angreifer untereinander (strength_a).
- 6.D.10/6.D.11 "SELF DISLODGMENT (OF A RETURNING UNIT) PROHIBITED" (zugrundeliegendes
  Verbot); 6.D.14 "SUPPORTING A FOREIGN UNIT IS NOT ENOUGH TO PREVENT DISLODGMENT".
- Die Werte 0/1/2 selbst sind Gilgamesch-IX.3-Varianten: die DATC entscheidet nur den
  Einzelnangreifer-Fall (6.D.12), nicht den Mehrfachangreifer-Fall.
Engine-Verhalten (Charakterisierung in tests/test_rule_interpretations.py): In der
k4-Kettenwiederholung ($chain4) konvergieren die Werte 0 und 2 -- nachdem die übrigen
Angreifer zu umove wurden, wird der a-Gewinner allein erneut geprüft und bei Wert 0
genauso abgelehnt wie bei Wert 2, wenn seine b-Stärke die Verteidigung nicht übersteigt.
Deutlich unterschieden wirkt Wert 0 daher nur im k2-Einzel-Resolve (angegriffener
Unterstützer, DATC 6.D.17/6.D.18): dort verdrängt der a-Gewinner, sofern irgendein
Angreifer auch ohne die Ziel-Nation-Unterstützungen die Verteidigung übersteigt.
"""


_ri_9_7 = """
**rule_interpretation_IX_7**

Bei einem Head-to-Head (Paar gegenseitiger mve, k3-Randkonflikt nach
Gilgamesch B.3.2.13) wird zuerst der Randkonflikt entschieden (Stärkevergleich
der beiden Bewegungen). Die Schalterwerte regeln, welche Wirkung die unterlegene
bzw. pattliegende Bewegung danach noch auf das Feld des Gegners hat:
- 0: Die unterlegene Bewegung behält ihre Wirkung, solange der Gewinner des
     Randkonflikts das Zielfeld nicht betreten kann -- sie zählt weiterhin als
     Angriff auf das Feld des Gewinners (u.a. Patt-Markierung gegen Dritte).
     Bei Patt am Rand bleiben beide Bewegungen als Angriffe aktiv.
- 1: Sobald der Randkonflikt entschieden ist, hat die unterlegene Bewegung keine
     Wirkung mehr (order=none). Bei Patt am Rand bleiben beide Bewegungen aktiv (wie 0).
- 2: Wie 1; zusätzlich haben bei Patt am Rand beide Bewegungen keine Wirkung
     ("the opposing moves have no effect").

DATC-Zuordnung (v3.2; verifiziert gegen testdata/datc-v3/DATC_v3_2.html): Die
Head-to-Head-Familie der DATC v3.2 ist Sektion 6.E ("HEAD-TO-HEAD BATTLES AND
BELEAGUERED GARRISON") -- NICHT 6.C (dort stehen die Kreisbewegungs-Fälle).
- Wert 0 (Default) ist DATC-konform: 6.E.4 "NON-DISLODGED LOSER STILL HAS EFFECT",
  6.E.5 "LOSER DISLODGED BY ANOTHER ARMY STILL HAS EFFECT", 6.E.6 "NOT DISLODGE
  BECAUSE OF OWN SUPPORT STILL HAS EFFECT" -- die unterlegene Bewegung wirkt auch
  nach dem verlorenen Randkonflikt noch auf das Feld des Gewinners.
- Die Werte 1/2 sind Gilgamesch-IX.7-Varianten ohne DATC-Entsprechung.
Siehe tests/test_rule_interpretations.py.
"""


class Switches(BaseModel):
    verbose: Optional[bool] = False
    self_cut_ok: Optional[bool] = Field(default=False, description=_ri_sc_ok)
    rule_interpretation_IX_3: Optional[int] = Field(default=0, ge=0, le=2, description=_ri_9_3)  # 0,1,2
    rule_interpretation_IX_7: Optional[int] = Field(default=0, description=_ri_9_7)  # 0,1,2
    convoy_cuts: Optional[bool] = False
    partial_cut_possible: Optional[int] = 0  # Not used for single-strengh-variant
    #
    convoy_routing_engine: Optional[str] = "always"
    strict_unit_types: Optional[bool] = Field(
        default=False,
        description=(
            "If True, unknown unit types and unit/field-type mismatches "
            "trigger SYN-002/SYN-007 strikes. Default off for std-Diplomacy "
            "where unit type is irrelevant for the conflict algorithm."
        ),
    )


# Subfield/superfield handling has moved to dipworkpy.geography.coast.
# The conflict resolver works on superfields only; Geography normalises
# 'SpN' to 'Spa' (and records the resolved coast in OrderGeoInfo) before
# the order set reaches the resolver.
class Situation(BaseModel):
    orders: List[Order] = []
    switches: Optional[Switches] = Switches()


########################
# results


def _decode_optional_bool(value: Optional[bool], on_true, on_false, on_none):
    if value is None:
        return on_none
    if value:
        return on_true
    return on_false


class OrderResult(BaseModel):  # could be derived from Order?
    nation: str
    utype: str = "A"  # TODO
    current: str  # current field name
    order: Optional[OrderType] = None  # mve, hld, con, sup
    dest: Optional[str] = None  # target field of mve, con, sup; may be None on hld
    # Defaults are None (== "no marker"), matching the writer's sparse
    # convention: it emits succeeds=False ONLY for actual failures and
    # dislodged=True ONLY for actually dislodged units. Successful,
    # non-dislodged orders carry no marker at all. This keeps the wire
    # form minimal and aligns with mk_oresult() in the test helpers.
    succeeds: Optional[bool] = None
    dislodged: Optional[bool] = None
    original: Optional[Order] = None  # may be None in tests, but usually set

    def __log__(self):
        s = _decode_optional_bool(self.succeeds, on_true="!!", on_false=" !", on_none="")
        d = _decode_optional_bool(self.dislodged, on_true=" >", on_false=">>", on_none="")
        o = self.order if self.order else ""
        t = self.dest if self.dest else ""
        orig = " (" + self.original.__log__() + ")" if self.original else ""
        return f"'{self.nation} {self.utype} {self.current} {o} {t} {s}{d}{orig}'"

    def __le__(self, other):
        """Like == but skips 'original'; Example: test_conflict_game_02.
        Not a pretty solution, but it allows the use of '<=' in assertions and keeping all information
        for analysis. But in general its better to use clear_originals() before ==."""
        # skip comparing 'original'
        for n in self.__class__.model_fields.keys():
            if n == "original":
                continue
            sv = getattr(self, n)
            ov = getattr(other, n)
            if sv is None and ov is None:
                continue  # both are None
            if sv is None or ov is None:
                return False  # only one is None
            if sv <= ov:
                continue
            return False
        return True


class ConflictResolution(BaseModel):
    orders: List[OrderResult]
    pattfields: Optional[Set[str]]  # fields unavailable for retreats

    def __log__(self):
        return ", ".join([o.__log__() for o in self.orders]) + "; " + str(self.pattfields)

    def __le__(self, other):
        """Not a pretty solution, but it allows the use of '<=' in assertions and keeping all information
        for analysis. But in general its better to use clear_originals() before ==. Example: test_conflict_game_02"""
        return self.orders <= other.orders and self.pattfields == other.pattfields

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
        print(f"{line_prefix}:", " ".join(sorted(self.pattfields or set())), file=f)


class ConflictCheck(BaseModel):
    nations: Set[str]
    utypes: Set[str]
    afields: Set[str]
    orders: Dict[OrderType, int]  # {'hld' : ..., }
    order_errors: int


########################
