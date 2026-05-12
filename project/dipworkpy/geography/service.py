"""geography_phase — pure function orchestrating GEO-001..009."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import OrderGeoInfo
from dipworkpy.geography.coast import normalize_to_superfield, resolve_coast
from dipworkpy.geography.convoy import build_convoy_graph
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.model import GeographyRequest, GeographyResponse
from dipworkpy.geography.rules import (
    classify_convoy,
    classify_move,
    classify_support,
)
from dipworkpy.model import Order, OrderType


def _diag(
    rule: str,
    severity: str,
    message: str,
    order_index: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Diagnostic:
    return Diagnostic(
        phase="geography",
        rule=rule,
        severity=severity,  # type: ignore[arg-type]
        order_index=order_index,
        message=message,
        details=details or {},
    )


def geography_phase(req: GeographyRequest) -> GeographyResponse:
    m = resolve_map_ref(req.map)
    out_orders: List[Order] = []
    geo_info: List[OrderGeoInfo] = []
    diagnostics: List[Diagnostic] = []

    # First pass: cmove classification needs all orders
    cmove_idx = build_convoy_graph(req.orders, m).cmove_candidates

    # Build a lookup: army_start -> convoyed_dest (from companion mve order)
    # so classify_convoy can know where the army is heading.
    army_dest_by_start: Dict[str, str] = {}
    for o in req.orders:
        if o.order == OrderType.mve and o.current and o.dest:
            army_dest_by_start[o.current] = o.dest

    for i, o in enumerate(req.orders):
        # Determine if `current` was a subfield (e.g. SpN) so we can record it
        # as the resolved coast for hold/support orders that sit on it.
        super_current = normalize_to_superfield(o.current, m)
        coast_from_current = (
            o.current if m.field_exists(o.current) and o.current != super_current else None
        )

        # Normalize: subfields in order refs collapse to superfields
        new_current = super_current
        new_dest = normalize_to_superfield(o.dest, m) if o.dest else None
        normalized = Order(
            nation=o.nation, utype=o.utype,
            current=new_current, order=o.order, dest=new_dest,
        )

        # Coast resolution for moves: look at the destination side
        resolved_coast = resolve_coast(o, m) or coast_from_current

        if o.order == OrderType.mve:
            info = classify_move(o, m, order_index=i)
            if i in cmove_idx:
                # Even if direct edge fails, presence of con orders allows
                # the cmove path. Override to moves+is_convoy_move.
                info.is_valid = True
                info.invalidity_code = None
                info.invalidity_reason = None
                info.effective_behavior = "moves"
                info.is_convoy_move = True
        elif o.order in (OrderType.hsup, OrderType.msup):
            # supported_target = o.dest (location of supported unit per
            # DipworkPy notation)
            target = o.dest if o.dest else o.current
            info = classify_support(o, m, supported_target=target, order_index=i)
        elif o.order == OrderType.con:
            # convoyed_dest is the actual move destination of the army.
            # In DipworkPy notation, con.dest = army start field; we look up
            # the army's actual move destination via the companion mve order.
            if o.dest is None or o.dest not in army_dest_by_start:
                info = OrderGeoInfo(
                    order_index=i, is_valid=False,
                    invalidity_code="GEO-006",
                    invalidity_reason=(
                        f"no companion mve order found for convoyed army "
                        f"at {o.dest!r}"
                    ),
                    effective_behavior="holds_supportable",
                )
            else:
                convoyed_dest = army_dest_by_start[o.dest]
                info = classify_convoy(
                    o, m, convoyed_dest=convoyed_dest, order_index=i,
                )
        else:  # hld or None
            info = OrderGeoInfo(
                order_index=i, is_valid=True,
                effective_behavior="holds_explicit",
            )

        if resolved_coast:
            info.resolved_coast = resolved_coast

        diagnostics.append(_diag(
            info.invalidity_code or "GEO-OK",
            "info" if info.is_valid else "correction",
            info.invalidity_reason or "ok",
            order_index=i,
        ))
        out_orders.append(normalized)
        geo_info.append(info)

    cg = build_convoy_graph(req.orders, m)

    return GeographyResponse(
        orders=out_orders, order_geo_info=geo_info,
        convoy_graph=cg, diagnostics=diagnostics,
    )
