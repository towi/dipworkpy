"""Order pre-processor subfield (coast) checks -- DATC 6.B coast rules.

The pre-processor (dipworkpy.order_prep) owns the subfield normalization
AND validation BEFORE the conflict: the conflicter is superfield-only and
blind to coasts. Coast-exact errors are corrected to HOLDS for the
conflicter (full defensive strength, no effect).

Standard-map facts used below (verified via geography.rules):
- Con borders BOTH Bul coasts (BuE, BuS) -- an unnamed fleet move to Bul
  from Con is ambiguous (DATC 6.B.1).
- Rum borders only BuE; BLA only BuE; Gre only BuS.
- LYO borders SpS but not SpN.
- Spa/Pet/Bul are the split-coast provinces; Den (Pet) via PeN/PeS.
"""

from dipworkpy.geo_model import MapRef
from dipworkpy.model import Order, OrderType
from dipworkpy.order_prep import prep_orders, normalize_subfields
from dipworkpy.geography.service import resolve_map_ref
from dipworkpy.round.orchestrator import RoundRequest, round_full


def _f(cur, dest, order=OrderType.mve, via=False, nation="Tu", utype="F"):
    return Order(nation=nation, utype=utype, current=cur, order=order, dest=dest, via_convoy=via)


def test_prep_unnamed_ambiguous_coast_is_hold():
    """DATC 6.B.1: `F Con mve Bul` -- Con borders both Bul coasts, the coast
    is necessary but not named -> ILLEGAL -> corrected to a hold."""
    out = prep_orders([_f("Con", "Bul")])
    assert out[0].order == OrderType.hld
    assert out[0].dest is None


def test_prep_named_reachable_coast_ok():
    """`F Con mve Bul/ec` -- named and reachable -> valid; normalized to the
    superfield for the conflicter."""
    out = prep_orders([_f("Con", "BuE")])
    assert out[0].order == OrderType.mve
    assert out[0].dest == "Bul"  # normalized superfield
    assert out[0].current == "Con"


def test_prep_unnamed_single_coast_auto_resolves():
    """DATC 6.B.2: `F Rum mve Bul` -- only BuE is reachable from Rum ->
    the coast is not necessary -> the move stands (auto-resolved)."""
    out = prep_orders([_f("Rum", "Bul")])
    assert out[0].order == OrderType.mve
    assert out[0].dest == "Bul"


def test_prep_named_unreachable_coast_is_hold():
    """DATC 6.B.3: `F BLA mve Bul/sc` -- the named coast is not reachable
    from BLA (only BuE is) -> ILLEGAL -> hold."""
    out = prep_orders([_f("BLA", "BuS")])
    assert out[0].order == OrderType.hld


def test_prep_armies_have_no_coast_semantics():
    """`A Con mve Bul` -- armies never trip the coast rules."""
    out = prep_orders([_f("Con", "Bul", nation="Tu", utype="A")])
    assert out[0].order == OrderType.mve
    assert out[0].dest == "Bul"


def test_prep_coast_cannot_be_ordered_to_change():
    """DATC 6.B.11: the fleet's ACTUAL position coast governs the move: a
    fleet on SpN cannot move to LYO (only SpS borders LYO), even though the
    superfields Spa and LYO are adjacent -> hold."""
    out = prep_orders([_f("SpN", "LYO", nation="Fr")])
    assert out[0].order == OrderType.hld


def test_prep_from_actual_coast_ok():
    """The same move from the fleet's south coast is fine."""
    out = prep_orders([_f("SpS", "LYO", nation="Fr")])
    assert out[0].order == OrderType.mve
    assert out[0].current == "Spa"  # normalized
    assert out[0].dest == "LYO"


def test_prep_support_from_unreachable_coast_is_hold():
    """DATC 6.B.5: a fleet on BuS cannot support a move to Rum (BuS does
    not border Rum) -> the support is ILLEGAL -> hold. (stpsyr 6.b test 5.)"""
    orders = [
        _f("BuS", "Bud", order=OrderType.msup, nation="Tu"),
        Order(nation="Au", utype="A", current="Bud", order=OrderType.mve, dest="Rum"),
    ]
    out = prep_orders(orders)
    assert out[0].order == OrderType.hld


def test_prep_support_from_reachable_coast_ok():
    """A fleet on BuS CAN support a unit on Gre (BuS borders Gre) -- and
    supporting TO a coast the supporter cannot reach is fine (6.B.4)."""
    orders = [
        _f("BuS", "Gre", order=OrderType.hsup, nation="Tu"),
        Order(nation="It", utype="A", current="Gre", order=OrderType.hld),
    ]
    out = prep_orders(orders)
    assert out[0].order == OrderType.hsup


def test_normalize_subfields_rewrites_refs():
    m = resolve_map_ref(MapRef())
    orders = [
        _f("BuS", "SpN", nation="Tu"),
        _f("PeS", "PeN", order=OrderType.hsup, nation="Ru"),
    ]
    out = normalize_subfields(orders, m)
    assert out[0].current == "Bul" and out[0].dest == "Spa"
    assert out[1].current == "Pet" and out[1].dest == "Pet"


def test_subfield_checks_coast_crawl_blocked():
    """`F SpN mve Spa` (moving to a coast of one's own province) never
    happens: the pre-processor normalizes it to the self-move
    `F Spa mve Spa`, which the geography phase strikes (GEO-003, a move to
    one's own field is illegal) -- the unit stays put (DATC: coastal crawl
    is not a move)."""
    out = prep_orders([_f("SpN", "Spa", nation="Fr")])
    assert out[0].current == out[0].dest == "Spa"  # normalized self-move
    rr = round_full(
        RoundRequest(
            orders=[_f("SpN", "Spa", nation="Fr")],
            unit_positions={"Spa": ("Fr", "F")},
        )
    )
    by = {o.current: o for o in rr.conflict.resolution.orders}
    assert by["Spa"].order == OrderType.hld  # GEO-003 struck; stays put


def test_round_full_hold_correction_end_to_end():
    """End to end through round_full: the ambiguous `F Con mve Bul` stands
    as a hold with full defensive strength; an unsupported attack on Con
    bounces (stpsyr 6.b test 1's ruling)."""
    rr = round_full(
        RoundRequest(
            orders=[
                _f("Con", "Bul"),
                Order(nation="Ru", utype="A", current="Gre", order=OrderType.mve, dest="Con"),
            ],
            unit_positions={"Con": ("Tu", "F"), "Gre": ("Ru", "A")},
        )
    )
    by = {o.current: o for o in rr.conflict.resolution.orders}
    assert by["Con"].order == OrderType.hld  # corrected, not a failed move
    assert by["Con"].succeeds is None  # a plain hold
    assert by["Con"].dislodged is None  # full strength -> bounce
    assert by["Gre"].succeeds is False


def test_round_full_auto_coast_move_end_to_end():
    """End to end: `F Rum mve Bul` (single reachable coast) still moves."""
    rr = round_full(
        RoundRequest(
            orders=[_f("Rum", "Bul", nation="Ru")],
            unit_positions={"Rum": ("Ru", "F")},
        )
    )
    by = {o.current: o for o in rr.conflict.resolution.orders}
    assert by["Rum"].order == OrderType.mve
    assert by["Rum"].succeeds is None
