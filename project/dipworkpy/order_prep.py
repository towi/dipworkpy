"""Rudimentary order pre-processor -- the phase BEFORE the conflict.

Architecture: the conflicter is deliberately independent of geography and
of rule switches. Whether a move goes by land (mve) or by convoy (cmve) is
decided HERE, not inside the conflict: the pre-processor rewrites convoy
moves to ``OrderType.cmve`` and the conflicter accepts that verdict as-is
(a cmve whose route is dead fails in k1 via $criv/$fn6 -- no land fallback).

Currently implemented (rudimentary):
- cmve conversion per the ``convoy_via_explicit`` switch (default False):
    * False (standard Diplomacy): the [Convoy] flag (Order.via_convoy) is
      purely informational; a move becomes a cmve exactly when some ordered
      convoyer convoying this movement exists -- adjacent or not, which
      makes the swap of two adjacent armies possible.
    * True (Gilgamesch B.3.2.14 scharf): a flagged move is always a cmve;
      unflagged adjacent moves stay land moves even when a convoy is
      ordered (Satz 3); unflagged non-adjacent moves use the convoy.

Later (not yet): subfield -> superfield normalization for the conflicter
( geography normalizes subfields today; that step is to move in here).

The classification core lives in dipworkpy.geography.convoy
(classify_cmove_candidates) so the geography phase (which still computes
cmove_candidates for graph-based callers) and the pre-processor share ONE
source of truth.
"""

from __future__ import annotations

from typing import List

from dipworkpy.geo_model import MapRef
from dipworkpy.geography.convoy import classify_cmove_candidates
from dipworkpy.geography.rules import can_reach_by_unit
from dipworkpy.geography.service import resolve_map_ref
from dipworkpy.model import Order, OrderType, Situation, Switches


def prep_orders(
    orders: List[Order],
    map_ref: MapRef | None = None,
    switches: Switches | None = None,
) -> List[Order]:
    """Rewrite convoy moves to OrderType.cmve (pre-conflict step)."""
    switches = switches or Switches()
    m = resolve_map_ref(map_ref or MapRef())
    via_explicit = bool(switches.convoy_via_explicit)
    orders = normalize_subfields(subfield_checks(orders, m), m)
    candidates = classify_cmove_candidates(orders, m, via_explicit=via_explicit)
    return [o.model_copy(update={"order": OrderType.cmve}) if i in candidates else o for i, o in enumerate(orders)]


def prep_situation(
    situation: Situation,
    map_ref: MapRef | None = None,
) -> Situation:
    """Convenience wrapper for direct conflict_game callers: run the
    pre-processor on a Situation and return the prepped Situation."""
    return Situation(
        orders=prep_orders(situation.orders, map_ref, situation.switches),
        switches=situation.switches,
    )


# ---------------------------------------------------------------------------
# Subfield (coast) checks + normalization -- DATC 6.B coast rules.
# These run on the RAW orders (subfield refs may appear in current/dest)
# BEFORE the superfield normalization: the coast information is needed for
# the checks and is discarded by the normalization.
# ---------------------------------------------------------------------------


def _to_hold(o: Order) -> Order:
    """Rewrite an invalid order as an explicit hold for the conflicter
    (full defensive strength, no effect) -- DATC 'illegal order'."""
    return o.model_copy(update={"order": OrderType.hld, "dest": None, "via_convoy": False})


def subfield_checks(orders: List[Order], m) -> List[Order]:
    """Coast (subfield) validation on raw orders (DATC 6.B.1-5, 6.B.11):

    Fleet moves to a multi-coast province:
      - 6.B.1 unnamed coast, MORE than one coast reachable -> ILLEGAL -> hold
      - 6.B.2 unnamed coast, exactly ONE coast reachable -> auto-resolve (ok)
      - 6.B.3 named coast that is NOT reachable -> ILLEGAL -> hold
    Armies: no coast semantics at all.

    Fleet supports (hsup/msup) from a COAST position (subfield in current):
      - 6.B.5 the supported province must be reachable from that coast;
        otherwise the support is ILLEGAL -> hold.
        (6.B.4: supporting TO a coast the fleet cannot reach is fine -- the
        check is about the SUPPORTER's position coast, not the target coast.)
    """
    # companion-move lookup: superfield start -> its mve order (msup target)
    mve_by_current: dict = {}
    for o in orders:
        if o.order == OrderType.mve and o.current:
            key = m.superfield_of(o.current) if m.field_exists(o.current) else o.current
            mve_by_current.setdefault(key, o)

    out: List[Order] = []
    for o in orders:
        repl = o
        if o.order == OrderType.mve and o.utype == "F" and o.dest and m.field_exists(o.dest):
            dest_super = m.superfield_of(o.dest)
            subs = m.subfields_of(dest_super)
            # exact position coast: a known subfield current stays exact
            # (6.B.11: the fleet's ACTUAL coast governs the move); an
            # unknown split-coast position is expanded leniently.
            cur = o.current if m.field_exists(o.current) else None
            exact_pos = cur is not None and m.superfield_of(cur) != cur
            if exact_pos:
                positions = [cur]
            elif cur is not None:
                positions = m.subfields_of(cur) or [cur]
            else:
                positions = [o.current]
            dest_exact = bool(subs) and o.dest != dest_super
            dests = [o.dest] if dest_exact else (subs or [o.dest])
            reach = [d for d in dests if any(can_reach_by_unit(p, d, "F", m, expand_dest=False) for p in positions)]
            if dest_exact:
                # named coast: legal iff reachable from the position (6.B.3,
                # 6.B.11)
                if not reach:
                    repl = _to_hold(o)
            elif subs:
                # unnamed coast of a split dest
                if len(reach) > 1:
                    repl = _to_hold(o)  # 6.B.1: coast necessary, not named
                # exactly one -> 6.B.2 auto-resolve; none -> GEO-003 below
            elif exact_pos and not reach:
                # non-split dest unreachable from the KNOWN position coast:
                # 6.B.11 / coastal crawl -- the fleet cannot move "through"
                # its province. (Only when the position coast is known;
                # otherwise the superfield-level GEO-003 applies.)
                repl = _to_hold(o)
        elif o.order in (OrderType.msup, OrderType.hsup) and o.utype == "F":
            if o.current and m.field_exists(o.current) and m.superfield_of(o.current) != o.current:
                # supporter on a KNOWN coast: 6.B.5 strict check
                target = o.dest
                if o.order == OrderType.msup and o.dest:
                    comp = mve_by_current.get(m.superfield_of(o.dest) if m.field_exists(o.dest) else o.dest)
                    if comp is not None and comp.dest:
                        target = comp.dest  # the supported MOVE's destination
                if target and m.field_exists(target):
                    if not can_reach_by_unit(o.current, target, "F", m, expand_dest=False):
                        repl = _to_hold(o)
        out.append(repl)
    return out


def normalize_subfields(orders: List[Order], m) -> List[Order]:
    """Rewrite all field refs to superfields -- the conflicter (and the
    downstream geography phase) are superfield-only (B.4.2 GEO-008)."""

    def _norm(fld):
        if fld and m.field_exists(fld):
            return m.superfield_of(fld)
        return fld

    return [o.model_copy(update={"current": _norm(o.current), "dest": _norm(o.dest)}) for o in orders]
