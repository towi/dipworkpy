"""DDL -> Situation / expected ConflictResolution."""
from __future__ import annotations

from collections import Counter
from typing import Set

from dipworkpy.model import (
    ConflictResolution, Order, OrderResult, OrderType, Situation,
)
from dipworkpy.tools.dwex.model import DwexDocument


def to_situation(doc: DwexDocument) -> Situation:
    orders = []
    for o in doc.orders:
        orders.append(Order(
            nation=o.nation, utype=o.utype, current=o.current,
            order=OrderType(o.order), dest=o.dest,
        ))
    return Situation(orders=orders)


def to_expected(doc: DwexDocument) -> ConflictResolution:
    """Translate DDL orders into the engine's post-conflict OrderResult shape.

    Engine post-conflict semantics (see test_conflict_game.py):
      - hld           -> order=hld, dest=current
      - successful mve -> order=mve, dest=dest
      - failed mve (!) -> order=hld, dest=intended-dest, succeeds=False
      - hsup / msup    -> order preserved, dest preserved
      - con            -> order preserved, dest preserved
    Plus pattfields: targets of two-or-more failed moves from different
    starts are bounced and the target is added.
    """
    results = []
    for o in doc.orders:
        order_type = OrderType(o.order)
        dest = o.dest
        out_order = order_type
        out_dest = dest
        if order_type == OrderType.hld:
            out_dest = o.current
        elif order_type == OrderType.mve:
            if o.expected_failed:
                # failed mve becomes hld with intended dest preserved
                out_order = OrderType.hld
                # out_dest = dest (intended target)

        results.append(OrderResult(
            nation=o.nation, utype=o.utype, current=o.current,
            order=out_order, dest=out_dest,
            succeeds=False if o.expected_failed else None,
            dislodged=True if o.expected_dislodged else None,
        ))

    # Compute pattfields: a destination contested by two-or-more failed mve orders.
    # If the user supplied expected_pattfields explicitly, use that instead.
    if doc.expected_pattfields:
        pattfields: Set[str] = set(doc.expected_pattfields)
    else:
        failed_targets: Counter = Counter()
        for o in doc.orders:
            if (OrderType(o.order) == OrderType.mve
                    and o.expected_failed and o.dest is not None):
                failed_targets[o.dest] += 1
        # A bounce on an *empty* target produces pattfields. If the target is
        # the current field of another (non-dislodged) order, it's defended,
        # not bounced. Only contested-empty targets enter pattfields.
        occupied = {o.current for o in doc.orders}
        pattfields = {
            t for t, n in failed_targets.items()
            if n >= 2 and t not in occupied
        }

    return ConflictResolution(orders=results, pattfields=pattfields)
