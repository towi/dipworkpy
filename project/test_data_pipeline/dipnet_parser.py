"""JSONL parser for the diplomacy/research dataset.

Reads standard_no_press.jsonl (one game per line), extracts movement phases,
and translates them into DwpcrTestCase objects for evaluation.
"""

import json
from dataclasses import dataclass, field
from typing import Iterator, List, Optional, TextIO

from dipworkpy.model import Order, OrderResult

from .mappings import (
    NATION_MAP,
    convert_territory,
    map_result,
    parse_dipnet_order,
)


@dataclass
class DwpcrTestCase:
    """A single test case for the DipworkPy conflict resolution engine.

    Fully self-contained: no shared mutable state. Each instance holds all
    information needed to run and evaluate the test independently.
    This enables future parallelization via multiprocessing.Pool.map().
    """

    id: str  # "gameId_S1901M"
    orders: List[Order]  # DipworkPy Order objects (input)
    expected: List[OrderResult]  # expected DipworkPy results
    has_convoy: bool  # any convoy order present?
    has_void: bool  # any void result in source?
    source_phase: str  # original phase name (e.g., "S1901M")
    source_game: str  # original game ID
    parse_warnings: List[str] = field(default_factory=list)  # non-fatal parse issues
    # Indices into self.orders for orders that received a "void" result from
    # the dataset. Used by cluster reporter to characterise void-INCONCLUSIVE
    # cases by the specific orders that triggered the void label.
    void_order_indices: List[int] = field(default_factory=list)
    # Indices of support orders whose raw DipNet statement contradicts
    # the referenced unit's actual order (hold-support on a mover;
    # move-support with a different stated destination). Only the
    # intersection with void_order_indices gets rewritten to hld.
    mismatch_support_indices: List[int] = field(default_factory=list)


def _result_key_to_territory(key: str) -> str:
    """Extract territory from DipNet result key like 'A BUD' or 'F STP/SC'."""
    parts = key.split()
    return parts[1] if len(parts) >= 2 else parts[0]


def _result_key_to_utype(key: str) -> str:
    """Extract unit type from DipNet result key like 'A BUD'."""
    return key.split()[0]


def _support_mismatch(order_str: str, orders_by_loc: dict) -> bool:
    """True when a support statement contradicts the referenced unit's
    actual order. order_str like 'A MUN S A VIE - BUD' / 'A MUN S A VIE'."""
    parts = order_str.split()
    if len(parts) < 5 or parts[2] != "S":
        return False
    ref_loc = convert_territory(parts[4])
    actual = orders_by_loc.get(ref_loc)
    if actual is None:
        return True  # support of a non-existent order
    aparts = actual.split()
    actual_is_move = len(aparts) >= 4 and aparts[2] == "-"
    if len(parts) >= 7 and parts[5] == "-":  # stated support-to-move
        if not actual_is_move:
            return True
        return convert_territory(parts[6]) != convert_territory(aparts[3])
    return actual_is_move  # stated support-to-hold on a mover


def parse_movement_phase(phase: dict, game_id: str) -> Optional[DwpcrTestCase]:
    """Parse a single movement phase into a DwpcrTestCase.

    Returns None if the phase has no orders or results.
    """
    phase_name = phase["name"]
    orders_by_nation = phase.get("orders") or {}
    results_by_unit = phase.get("results") or {}

    if not orders_by_nation or not results_by_unit:
        return None

    test_id = f"{game_id}_{phase_name}"
    dwp_orders: List[Order] = []
    dwp_expected: List[OrderResult] = []
    void_order_indices: List[int] = []
    mismatch_support_indices: List[int] = []
    has_convoy = False
    has_void = False
    warnings: List[str] = []

    # Build a lookup: (utype, dwp_territory) → result_list
    result_lookup: dict[tuple[str, str], list[str]] = {}
    for result_key, result_list in results_by_unit.items():
        try:
            utype = _result_key_to_utype(result_key)
            terr_dipnet = _result_key_to_territory(result_key)
            terr_dwp = convert_territory(terr_dipnet)
            result_lookup[(utype, terr_dwp)] = result_list
        except KeyError:
            warnings.append(f"Unknown territory in result key: {result_key}")

    # Build a raw-order lookup keyed by the unit's location, so support
    # statements can be checked against the referenced unit's actual order.
    orders_by_loc: dict[str, str] = {}
    for order_list in orders_by_nation.values():
        if order_list is None:
            continue
        for order_str in order_list:
            parts = order_str.split()
            if len(parts) < 2:
                continue
            try:
                orders_by_loc[convert_territory(parts[1])] = order_str
            except KeyError:
                continue

    # Parse orders for each nation
    for nation_dipnet, order_list in orders_by_nation.items():
        if order_list is None:
            continue
        nation_dwp = NATION_MAP.get(nation_dipnet)
        if nation_dwp is None:
            warnings.append(f"Unknown nation: {nation_dipnet}")
            continue

        for order_str in order_list:
            # Check for convoy markers
            if " C " in order_str or order_str.endswith(" VIA"):
                has_convoy = True

            try:
                order = parse_dipnet_order(order_str, nation_dwp)
            except (KeyError, IndexError, ValueError) as e:
                warnings.append(f"Failed to parse order '{order_str}': {e}")
                continue

            dwp_orders.append(order)

            # Flag support statements that contradict the referenced unit's
            # actual order (unrepresentable in msup notation). Only the
            # intersection with void_order_indices is later rewritten to hld.
            try:
                if _support_mismatch(order_str, orders_by_loc):
                    mismatch_support_indices.append(len(dwp_orders) - 1)
            except (KeyError, IndexError) as e:
                warnings.append(f"Could not check support mismatch for '{order_str}': {e}")

            # Find matching result
            lookup_key = (order.utype, order.current)
            result_list = result_lookup.get(lookup_key, [])

            if "void" in result_list:
                has_void = True
                void_order_indices.append(len(dwp_orders) - 1)

            succeeds, dislodged = map_result(result_list)

            expected = OrderResult(
                nation=order.nation,
                utype=order.utype,
                current=order.current,
                order=order.order,
                dest=order.dest,
                succeeds=succeeds,
                dislodged=dislodged,
            )
            dwp_expected.append(expected)

    if not dwp_orders:
        return None

    return DwpcrTestCase(
        id=test_id,
        orders=dwp_orders,
        expected=dwp_expected,
        has_convoy=has_convoy,
        has_void=has_void,
        source_phase=phase_name,
        source_game=game_id,
        parse_warnings=warnings,
        void_order_indices=void_order_indices,
        mismatch_support_indices=mismatch_support_indices,
    )


def parse_game_line(json_line: str) -> List[DwpcrTestCase]:
    """Parse one JSONL line (one game) into a list of DwpcrTestCase.

    Each movement phase (name ending with 'M') becomes one test case.
    """
    game = json.loads(json_line)
    game_id = game.get("id", "unknown")
    phases = game.get("phases", [])
    test_cases: List[DwpcrTestCase] = []

    for phase in phases:
        phase_name = phase.get("name", "")
        if not phase_name.endswith("M"):
            continue

        tc = parse_movement_phase(phase, game_id)
        if tc is not None:
            test_cases.append(tc)

    return test_cases


def stream_test_cases(jsonl_file: TextIO, max_games: Optional[int] = None) -> Iterator[DwpcrTestCase]:
    """Stream DwpcrTestCase objects from an open JSONL file.

    Args:
        jsonl_file: Open file handle for standard_no_press.jsonl
        max_games: If set, stop after this many game lines

    Yields:
        DwpcrTestCase for each movement phase in each game
    """
    for game_num, line in enumerate(jsonl_file):
        if max_games is not None and game_num >= max_games:
            break
        line = line.strip()
        if not line:
            continue
        for tc in parse_game_line(line):
            yield tc
