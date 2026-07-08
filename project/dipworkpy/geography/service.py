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

    # First pass: convoy classification needs all orders.
    cg = build_convoy_graph(req.orders, m)
    cmove_idx = cg.cmove_candidates

    # Build a lookup: army_start -> convoyed_dest (from companion mve order)
    # so classify_convoy can know where the army is heading.
    army_dest_by_start: Dict[str, str] = {}
    for o in req.orders:
        if o.order == OrderType.mve and o.current and o.dest:
            army_start = normalize_to_superfield(o.current, m)
            army_dest_by_start[army_start] = normalize_to_superfield(o.dest, m)

    for i, o in enumerate(req.orders):
        # Determine if `current` was a subfield (e.g. SpN) so we can record it
        # as the resolved coast for hold/support orders that sit on it.
        super_current = normalize_to_superfield(o.current, m)
        coast_from_current = o.current if m.field_exists(o.current) and o.current != super_current else None

        # Normalize: subfields in order refs collapse to superfields
        new_current = super_current
        new_dest = normalize_to_superfield(o.dest, m) if o.dest else None
        normalized = Order(
            nation=o.nation,
            utype=o.utype,
            current=new_current,
            order=o.order,
            dest=new_dest,
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
            # DipworkPy notation). For msup, GEO-004 must check the
            # supported MOVE's destination, looked up via the companion
            # mve order (army_dest_by_start indexes all movers).
            target_raw = o.dest if o.dest else o.current
            target = normalize_to_superfield(target_raw, m)
            info = classify_support(
                o,
                m,
                supported_target=target,
                order_index=i,
                move_dest=army_dest_by_start.get(target),
                is_msup=(o.order == OrderType.msup),
            )
        elif o.order == OrderType.con:
            # convoyed_dest is the actual move destination of the army.
            # In DipworkPy notation, con.dest = army start field; we look up
            # the army's actual move destination via the companion mve order.
            con_army_start = normalize_to_superfield(o.dest, m) if o.dest else None
            if con_army_start is None or con_army_start not in army_dest_by_start:
                info = OrderGeoInfo(
                    order_index=i,
                    is_valid=False,
                    invalidity_code="GEO-006",
                    invalidity_reason=(f"no companion mve order found for convoyed army at {o.dest!r}"),
                    effective_behavior="holds_supportable",
                )
            else:
                convoyed_dest = army_dest_by_start[con_army_start]
                info = classify_convoy(
                    o,
                    m,
                    convoyed_dest=convoyed_dest,
                    order_index=i,
                    convoy_graph=cg,
                )
        else:  # hld or None
            info = OrderGeoInfo(
                order_index=i,
                is_valid=True,
                effective_behavior="holds_explicit",
            )

        if resolved_coast:
            info.resolved_coast = resolved_coast
            diagnostics.append(
                _diag(
                    "GEO-007",
                    "info",
                    f"coast resolved to {resolved_coast!r} for fleet on {super_current!r}",
                    order_index=i,
                )
            )

        # GEO-008: emit when the on-the-wire form (current, dest) differs from
        # the user-supplied form because a subfield was collapsed to its
        # superfield. Lets the UI show "we rewrote SpN → Spa for you" without
        # the caller having to diff orders themselves.
        normalized_changed = (new_current != o.current) or (o.dest is not None and new_dest != o.dest)
        if normalized_changed:
            diagnostics.append(
                _diag(
                    "GEO-008",
                    "info",
                    f"normalised to superfield(s): "
                    f"{o.current!r}->{new_current!r}" + (f", {o.dest!r}->{new_dest!r}" if o.dest != new_dest else ""),
                    order_index=i,
                )
            )

        diagnostics.append(
            _diag(
                info.invalidity_code or "GEO-OK",
                "info" if info.is_valid else "correction",
                info.invalidity_reason or "ok",
                order_index=i,
            )
        )
        out_orders.append(normalized)
        geo_info.append(info)

    return GeographyResponse(
        orders=out_orders,
        order_geo_info=geo_info,
        convoy_graph=cg,
        diagnostics=diagnostics,
    )
