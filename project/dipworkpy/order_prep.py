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
