"""Retreat candidate ordering based on ordered border rings."""

from __future__ import annotations

from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.model import RetreatOptionsRequest, RetreatOptionsResponse
from dipworkpy.geography.rules import can_reach_by_unit

EXIT_TOKEN = "ex"


def _right_hand_order(ring: list[str], attacked_from: str) -> list[str]:
    if attacked_from not in ring:
        return [n for n in ring if n != attacked_from]
    origin = ring.index(attacked_from)
    ordered: list[str] = []
    for distance in range(1, len(ring)):
        clockwise = ring[(origin + distance) % len(ring)]
        if clockwise not in ordered and clockwise != attacked_from:
            ordered.append(clockwise)
        counter_clockwise = ring[(origin - distance) % len(ring)]
        if counter_clockwise not in ordered and counter_clockwise != attacked_from:
            ordered.append(counter_clockwise)
    return ordered


def retreat_options(req: RetreatOptionsRequest) -> RetreatOptionsResponse:
    m = resolve_map_ref(req.map)
    ring = m.neighbor_order(req.field) if m.field_exists(req.field) else []
    occupied = {m.superfield_of(f) if m.field_exists(f) else f for f in req.occupied_fields}

    candidates: list[str] = []
    for candidate in _right_hand_order(ring, req.attacked_from):
        candidate_super = m.superfield_of(candidate) if m.field_exists(candidate) else candidate
        if candidate_super in occupied:
            continue
        if not can_reach_by_unit(req.field, candidate, req.utype, m, expand_dest=False):
            continue
        candidates.append(candidate)

    candidates.append(EXIT_TOKEN)
    return RetreatOptionsResponse(
        field=req.field,
        attacked_from=req.attacked_from,
        candidates=candidates,
    )
