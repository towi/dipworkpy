"""DDL -> Situation / expected ConflictResolution."""
from __future__ import annotations

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
    results = []
    for o in doc.orders:
        results.append(OrderResult(
            nation=o.nation, utype=o.utype, current=o.current,
            order=OrderType(o.order), dest=o.dest,
            succeeds=False if o.expected_failed else None,
            dislodged=True if o.expected_dislodged else None,
        ))
    return ConflictResolution(orders=results, pattfields=doc.expected_pattfields)
