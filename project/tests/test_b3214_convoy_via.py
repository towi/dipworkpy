"""Switch `convoy_via_explicit` (Gilgamesch B.3.2.14 Satz 1) -- switch-position tests.

The switch NEVER acts inside the conflicter: the order pre-processor
(dipworkpy.order_prep, classification core in geography.convoy) rewrites
convoy moves to OrderType.cmve before the conflict, and the conflicter
accepts that verdict as-is.

Default False (standard Diplomacy / Dippy / DipNet style): the [Convoy] flag
(Order.via_convoy) is purely informational. A move -- adjacent or not --
becomes a convoy move exactly when some ordered convoyer convoying this
movement exists (the con order "claims" the move). Consequences:
- two adjacent armies can SWAP when one move is claimed by a con order;
- a CLAIMED adjacent move with a DISRUPTED convoy STANDS (no land fallback).

True (Gilgamesch B.3.2.14 scharf): a flagged move is a convoy move
regardless of con orders (no land fallback; dead route -> $criv stand at
full strength). Unflagged adjacent moves stay land moves even when a convoy
is ordered (Satz 3); unflagged non-adjacent moves use the convoy.

Topology (standard map, verified via geography.rules.can_reach_by_unit):
Con-Bul is an army land edge; both coasts touch Bla (Black Sea); Lon-Bre
has NO land route for armies; ENG convoys Lon->Bre.
"""

from dipworkpy.geo_model import MapRef
from dipworkpy.geography.convoy import classify_cmove_candidates
from dipworkpy.geography.service import resolve_map_ref
from dipworkpy.model import Order, OrderType, Switches
from dipworkpy.round.orchestrator import RoundRequest, round_full


def _flagged(nation, utype, current, dest):
    return Order(nation=nation, utype=utype, current=current, order=OrderType.mve, dest=dest, via_convoy=True)


def _res(orders, positions, switches=None):
    kwargs = {}
    if switches is not None:
        kwargs["switches"] = switches
    return round_full(RoundRequest(orders=orders, unit_positions=positions, **kwargs))


def test_default_flagged_adjacent_move_goes_by_land():
    """Default: a flagged move to an ADJACENT field with NO con order
    anywhere (the DipNet VIA case: `Tu A Con mve Bul via_convoy=True`,
    zero cons) is a plain land move and SUCCEEDS."""
    res = _res(
        [_flagged("Tu", "A", "Con", "Bul")],
        {"Con": ("Tu", "A")},
    )
    geo = res.geography.order_geo_info[0]
    assert geo.is_valid is True
    assert geo.is_convoy_move is False  # flag ignored -> land move
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Con"].order == OrderType.mve
    assert by["Con"].succeeds is None  # moved by land
    assert not res.geography.convoy_graph.cmove_candidates


def test_default_con_order_claims_adjacent_move():
    """Default: a con order convoying an ADJACENT move claims it as a convoy
    move (flagged or not) -- the army crosses by sea, not by land."""
    res = _res(
        [
            _flagged("Ge", "A", "Pic", "Bel"),
            Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Pic"),
        ],
        {"Pic": ("Ge", "A"), "ENG": ("En", "F")},
    )
    geo = res.geography.order_geo_info[0]
    assert geo.is_valid is True
    assert geo.is_convoy_move is True  # claimed by the con order
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Pic"].order == OrderType.mve
    assert by["Pic"].succeeds is None  # crossed by convoy


def test_default_adjacent_armies_swap_via_convoy():
    """Default (the user's example): `A Con mve Bul`, `A Bul mve Con`,
    `F Bla con Con` -- the con order claims Con->Bul as a convoy move, so
    the two adjacent armies SWAP (cmove vs nmove: no border conflict,
    B.3.2.13/C.2.3)."""
    res = _res(
        [
            Order(nation="Tu", utype="A", current="Con", order=OrderType.mve, dest="Bul"),
            Order(nation="Ru", utype="A", current="Bul", order=OrderType.mve, dest="Con"),
            Order(nation="Tu", utype="F", current="BLA", order=OrderType.con, dest="Con"),
        ],
        {"Con": ("Tu", "A"), "Bul": ("Ru", "A"), "BLA": ("Tu", "F")},
    )
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Con"].order == OrderType.mve  # moved (by convoy)
    assert by["Con"].succeeds is None
    assert by["Bul"].order == OrderType.mve  # moved (by land)
    assert by["Bul"].succeeds is None
    assert by["BLA"].order == OrderType.con
    assert by["BLA"].dislodged is None


def test_default_claimed_adjacent_move_stands_when_convoy_disrupted():
    """Default: a CLAIMED adjacent move has NO land fallback -- when the
    convoyer is dislodged, the army stands (failed move), even though it
    could have walked."""
    res = _res(
        [
            Order(nation="Ge", utype="A", current="Pic", order=OrderType.mve, dest="Bel"),  # adjacent, claimed below
            Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Pic"),
            Order(nation="Fr", utype="F", current="NTH", order=OrderType.mve, dest="ENG"),  # dislodges ENG
            Order(nation="Fr", utype="F", current="IRI", order=OrderType.msup, dest="NTH"),
        ],
        {"Pic": ("Ge", "A"), "ENG": ("En", "F"), "NTH": ("Fr", "F"), "IRI": ("Fr", "F")},
    )
    geo = res.geography.order_geo_info[0]
    assert geo.is_convoy_move is True
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["ENG"].dislodged is True
    assert by["Pic"].order == OrderType.hld  # dead route -> stands
    assert by["Pic"].succeeds is False  # the (convoy) move failed


def test_default_non_adjacent_still_moves_by_convoy():
    """Default: a flagged move with NO land route still goes by convoy --
    the convoy is the only way, no flag needed (unchanged for both switch
    positions)."""
    res = _res(
        [
            _flagged("En", "A", "Lon", "Bre"),
            Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Lon"),
        ],
        {"Lon": ("En", "A"), "ENG": ("En", "F")},
    )
    geo = res.geography.order_geo_info[0]
    assert geo.is_convoy_move is True
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Lon"].order == OrderType.mve
    assert by["Lon"].succeeds is None  # moved by convoy


def test_default_flagged_non_adjacent_without_convoy_stands_full_strength():
    """Default: a flagged move with NO land route and NO con order is an
    unambiguous convoy ATTEMPT (the flag names the intent) -> convoy move
    with a dead route -> $criv stand at FULL defensive strength (DipNet
    'no convoy'), NOT the B.4.2.9 def-0 umove."""
    res = _res(
        [_flagged("En", "A", "Lon", "Bre")],
        {"Lon": ("En", "A")},
    )
    geo = res.geography.order_geo_info[0]
    assert geo.is_valid is True
    assert geo.is_convoy_move is True
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Lon"].order == OrderType.hld  # $criv: stands
    assert by["Lon"].succeeds is False  # the convoy move failed
    assert by["Lon"].dislodged is None


def test_default_unflagged_non_adjacent_without_convoy_is_geo_invalid():
    """Default: an UNFLAGGED move without land route and without con order
    is geo-invalid (B.4.2.9 umove, def 0) -> succeeds=False; the unit stays."""
    res = _res(
        [Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="Bre")],
        {"Lon": ("En", "A")},
    )
    geo = res.geography.order_geo_info[0]
    assert geo.is_valid is False
    assert geo.effective_behavior == "holds_no_support"
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Lon"].succeeds is False  # B.4.2.9 umove reports failure


def test_explicit_switch_flagged_adjacent_stands():
    """Switch True (Gilgamesch B.3.2.14 Satz 1): the same Con->Bul order
    WITHOUT a convoyer stands ($criv) at full defensive strength."""
    res = _res(
        [_flagged("Tu", "A", "Con", "Bul")],
        {"Con": ("Tu", "A")},
        switches=Switches(convoy_via_explicit=True),
    )
    geo = res.geography.order_geo_info[0]
    assert geo.is_convoy_move is True  # flag forces the sea route
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Con"].order == OrderType.hld  # no route -> stands
    assert by["Con"].succeeds is False  # the convoy move FAILED (no land fallback)
    assert by["Con"].dislodged is None


def test_explicit_switch_flagged_adjacent_stands_at_full_strength():
    """Switch True: the standing flagged move keeps full defensive strength
    (Satz 1: 'bleibt stehen' -- a failed convoy move, not holds_no_support):
    an unsupported attack on it bounces."""
    res = _res(
        [
            _flagged("Tu", "A", "Con", "Bul"),
            Order(nation="Ru", utype="A", current="Gre", order=OrderType.mve, dest="Con"),
        ],
        {"Con": ("Tu", "A"), "Gre": ("Ru", "A")},
        switches=Switches(convoy_via_explicit=True),
    )
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Con"].order == OrderType.hld
    assert by["Con"].dislodged is None  # full strength -> attack bounces
    assert by["Gre"].succeeds is False


def test_explicit_switch_unflagged_adjacent_ignores_convoy():
    """Switch True (B.3.2.14 Satz 3): an UNFLAGGED adjacent move stays a
    land move even with an ordered convoy -- no swap, and a disrupted convoy
    does not stop it from walking."""
    res = _res(
        [
            Order(nation="Tu", utype="A", current="Con", order=OrderType.mve, dest="Bul"),  # NO flag
            Order(nation="Tu", utype="F", current="BLA", order=OrderType.con, dest="Con"),
        ],
        {"Con": ("Tu", "A"), "Bla": ("Tu", "F")},
        switches=Switches(convoy_via_explicit=True),
    )
    geo = res.geography.order_geo_info[0]
    assert geo.is_convoy_move is False  # Satz 3: land move
    by = {o.current: o for o in res.conflict.resolution.orders}
    assert by["Con"].order == OrderType.mve
    assert by["Con"].succeeds is None  # walked by land


def test_classifier_switch_positions():
    """Unit level: classify_cmove_candidates honours the switch.

    Order set: flagged adjacent Con->Bul + ordered convoyer (Bla) and an
    unflagged adjacent Bul->Con with no convoyer."""
    m = resolve_map_ref(MapRef())
    orders = [
        Order(nation="Tu", utype="A", current="Con", order=OrderType.mve, dest="Bul", via_convoy=True),
        Order(nation="Ru", utype="A", current="Bul", order=OrderType.mve, dest="Con"),
        Order(nation="Tu", utype="F", current="BLA", order=OrderType.con, dest="Con"),
    ]
    # default: the flag is informational; the con order claims Con->Bul
    assert classify_cmove_candidates(orders, m, via_explicit=False) == {0}
    # Gilgamesch: the flag alone makes Con->Bul a convoy move (route or not);
    # unflagged adjacent Bul->Con stays a land move (Satz 3)
    assert classify_cmove_candidates(orders, m, via_explicit=True) == {0}

    # flagged adjacent move with NO con order: only the switch makes it a
    # convoy move (no land fallback -> $criv stand)
    orders_ncon = [
        Order(nation="Tu", utype="A", current="Con", order=OrderType.mve, dest="Bul", via_convoy=True),
    ]
    assert classify_cmove_candidates(orders_ncon, m, via_explicit=False) == set()
    assert classify_cmove_candidates(orders_ncon, m, via_explicit=True) == {0}

    # unflagged adjacent move with a con order claiming it: the DEFAULT
    # convoys it (swap-capable); Gilgamesch Satz 3 keeps it on land
    orders_unflagged = [
        Order(nation="Tu", utype="A", current="Con", order=OrderType.mve, dest="Bul"),
        Order(nation="Tu", utype="F", current="BLA", order=OrderType.con, dest="Con"),
    ]
    assert classify_cmove_candidates(orders_unflagged, m, via_explicit=False) == {0}
    assert classify_cmove_candidates(orders_unflagged, m, via_explicit=True) == set()

    # cmve orders pass through (pre-processed input is idempotent)
    prepped = [orders[0].model_copy(update={"order": OrderType.cmve})] + orders[1:]
    assert classify_cmove_candidates(prepped, m, via_explicit=False) == {0}

    # default of the ENGINE switch is False
    assert Switches().convoy_via_explicit is False
