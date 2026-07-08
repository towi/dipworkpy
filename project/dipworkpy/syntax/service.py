"""syntax_phase - strikes invalid orders + injects hold-defaults."""

from __future__ import annotations

from collections import Counter
from typing import Any, List, Literal, Optional

from dipworkpy.diag import Diagnostic
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.model import Order, OrderType
from dipworkpy.syntax import rules
from dipworkpy.syntax.model import SyntaxRequest, SyntaxResponse


def _diag(
    rule: str,
    severity: Literal["info", "warning", "correction", "error"],
    message: str,
    idx: Optional[int] = None,
    **details: Any,
) -> Diagnostic:
    return Diagnostic(
        phase="syntax", rule=rule, severity=severity, order_index=idx, message=message, details=dict(details)
    )


KNOWN_NATIONS = {"Au", "En", "Fr", "Ge", "It", "Ru", "Tu"}


def syntax_phase(req: SyntaxRequest) -> SyntaxResponse:
    m = resolve_map_ref(req.map)
    sw = req.switches
    diags: List[Diagnostic] = []
    survivors: List[Order] = []

    # Detect doubles (SYN-005)
    counts = Counter(o.current for o in req.orders)
    double_fields = {f for f, c in counts.items() if c > 1}

    for i, o in enumerate(req.orders):
        if rules.is_unknown_nation(o, KNOWN_NATIONS):
            diags.append(_diag("SYN-001", "correction", f"unknown nation {o.nation!r}", idx=i))
            continue
        if rules.is_unknown_unit_type(o, sw):
            diags.append(_diag("SYN-002", "correction", f"unknown utype {o.utype!r}", idx=i))
            continue
        if not rules.has_known_order_type(o):
            diags.append(_diag("SYN-003", "correction", f"unknown order type {o.order!r}", idx=i))
            continue
        if not rules.field_exists(o, m):
            diags.append(_diag("SYN-004", "correction", f"unknown current field {o.current!r}", idx=i))
            continue
        if rules.is_unit_field_mismatch(o, m, sw):
            diags.append(_diag("SYN-007", "correction", f"unit type {o.utype!r} cannot stand on {o.current!r}", idx=i))
            continue
        if not rules.has_unit_at_current(o, req.unit_positions):
            diags.append(_diag("SYN-006", "correction", f"no unit at {o.current!r}", idx=i))
            continue
        if o.current in double_fields:
            diags.append(_diag("SYN-005", "correction", f"double order on {o.current}", idx=i))
            continue
        survivors.append(o)

    # SYN-008: inject hold-default for units without a surviving order
    ordered_fields = {o.current for o in survivors}
    for field, (nation, utype) in req.unit_positions.items():
        if field not in ordered_fields:
            survivors.append(
                Order(
                    nation=nation,
                    utype=utype,
                    current=field,
                    order=OrderType.hld,
                )
            )
            diags.append(_diag("SYN-008", "info", f"hold-default injected for {field}"))

    return SyntaxResponse(orders=survivors, diagnostics=diags)
