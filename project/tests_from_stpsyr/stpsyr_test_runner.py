#!/usr/bin/env python3
"""Python test runner for stpsyr DATC test cases.

Based on https://github.com/tckmn/stpsyr/blob/master/tests/lib.rs

Each case starts from the standard 1901 opening position (``STANDARD_START``)
and is stepped one movement phase at a time through ``round_full`` (syntax ->
geography -> conflict resolution). After the final phase the resulting board is
compared field-by-field against the file's expected results, producing a
PASS / FAIL / ERROR verdict per case. This replaced the earlier stopgap where
"pass" merely meant "did not throw" and the expected results were discarded.

Known limitations
-----------------
1. Retreat phases are applied NAIVELY. A block counts as a retreat phase only
   when *every* order references a unit that was just dislodged (datc-6.f.7 has
   exactly one such block). A single, uncontested retreat-move to an empty
   field succeeds; everything else disbands (the unit is already off the
   board). There is no retreat-CONFLICT resolution engine yet
   (see AGENTS.md Roadmap #3).
2. Superfield-only board. Coast-specific expectations in datc-6.b adjudicate
   only approximately, because both the engine and this board collapse coasts
   to their parent superfield (Task 10 bucket B).
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Local imports — must stay below the sys.path.insert so project/ resolves.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))  # project/ on sys.path
from dipworkpy.geo_model import MapRef  # noqa: E402
from dipworkpy.geography.service import resolve_map_ref  # noqa: E402
from dipworkpy.model import Order, OrderType, Switches  # noqa: E402
from test_data_pipeline.mappings import convert_territory  # noqa: E402

_MAP = None


def _super(fld: str) -> str:
    """Field -> superfield (BuS -> Bul); unknown fields pass through."""
    global _MAP
    if _MAP is None:
        _MAP = resolve_map_ref(MapRef())
    if _MAP.field_exists(fld):
        return _MAP.superfield_of(fld)
    return fld


# Standard 1901 opening position, superfield-only. Field -> (nation, utype).
# Russia's F StP/SC and the other coastal fleets collapse to their superfield
# (Pet, Seb, ...) — the engine and this board work on superfields only.
STANDARD_START: Dict[str, Tuple[str, str]] = {
    # Austria            # England            # France
    "Vie": ("Au", "A"),
    "Lon": ("En", "F"),
    "Par": ("Fr", "A"),
    "Bud": ("Au", "A"),
    "Edi": ("En", "F"),
    "Mar": ("Fr", "A"),
    "Tri": ("Au", "F"),
    "Lpl": ("En", "A"),
    "Bre": ("Fr", "F"),
    # Germany            # Italy              # Turkey
    "Ber": ("Ge", "A"),
    "Rom": ("It", "A"),
    "Con": ("Tu", "A"),
    "Mun": ("Ge", "A"),
    "Ven": ("It", "A"),
    "Smy": ("Tu", "A"),
    "Kie": ("Ge", "F"),
    "Nap": ("It", "F"),
    "Ank": ("Tu", "F"),
    # Russia (F StP/SC -> superfield Pet)
    "Mos": ("Ru", "A"),
    "War": ("Ru", "A"),
    "Seb": ("Ru", "F"),
    "Pet": ("Ru", "F"),
}


def apply_resolution(board, resolution, parsed_orders=None):
    """Advance the board one movement phase.

    Returns (new_board, dislodged_units); dislodged_units maps
    SUPERFIELD -> (nation, utype) for units knocked off the board this
    phase — the NEXT block may be their retreat phase (see run_test_case).

    succeeds: None == success, False == failed (never truth-test).
    A dislodged unit's field may simultaneously be the destination of
    the successful move that dislodged it — removal happens before
    arrivals are placed, so that is handled naturally.

    Board keys may be SUBFIELDS (BuS, SpN...) — the corpus compares at
    superfield level, but the coast-exact position survives for the NEXT
    phase's DATC 6.B checks: a successful move's arrival position is the
    order's RAW destination (subfield when the corpus names a coast), and
    vacating removes every key of the origin superfield.
    """
    raw_dest_by_start = {}
    for o in parsed_orders or []:
        raw_dest_by_start[(_super(o.current), o.nation, o.utype)] = o.dest
    moved = {}
    vacated = set()
    dislodged = {}
    for r in resolution.orders:
        if r.order == OrderType.mve and r.succeeds is None:
            vacated.add(r.current)
            arrival = raw_dest_by_start.get((r.current, r.nation, r.utype), r.dest)
            moved[arrival] = (r.nation, r.utype)
        if r.dislodged is True:
            dislodged[r.current] = (r.nation, r.utype)
    new_board = {f: u for f, u in board.items() if _super(f) not in vacated and _super(f) not in dislodged}
    new_board.update(moved)
    return new_board, dislodged


def expected_matches(board, territory, expectation, parse_nation_name):
    """Superfield-level comparison: board keys may be subfields (BuS)."""
    if expectation.lower() == "empty":
        return all(_super(k) != territory for k in board)
    parts = expectation.split()  # "Fleet England"
    if len(parts) != 2:
        return False
    utype = {"Fleet": "F", "Army": "A"}.get(parts[0])
    nation = parse_nation_name(parts[1])
    return any(_super(k) == territory and u == (nation, utype) for k, u in board.items())


@dataclass
class Phase:
    """One movement/adjustment step within a test case.

    A blank line in the DATC file separates phases. Movement phases carry
    ``orders``; adjustment phases carry ``builds`` and/or ``disbands``.
    """

    orders: List[Order]  # movement orders (may be empty for adjustment phases)
    builds: List[Tuple[str, str, str]]  # (nation, utype, territory) from "B F bre"
    disbands: List[str]  # territory from "D hel"


@dataclass
class TestCase:
    """Represents a single (possibly multi-phase) test case."""

    number: int
    title: str
    phases: List[Phase]
    expected_results: Dict[str, str]  # superfield -> "Fleet England"|"Army Italy"|"empty"


class StpsyrTestRunner:
    """Parser and runner for stpsyr-format DATC test files"""

    def __init__(self):
        self.test_cases: List[TestCase] = []

    def parse_nation_name(self, name: str) -> str:
        """Convert stpsyr nation names to DipworkPy notation"""
        name_map = {
            "England": "En",
            "France": "Fr",
            "Germany": "Ge",
            "Austria": "Au",
            "Italy": "It",
            "Russia": "Ru",
            "Turkey": "Tu",
        }
        return name_map.get(name, name[:2].upper())

    _COAST_SUBFIELDS = {
        "bul/ec": "BuE",
        "bul/sc": "BuS",
        "spa/nc": "SpN",
        "spa/sc": "SpS",
        "stp/nc": "PeN",
        "stp/sc": "PeS",
    }

    def parse_territory_name(self, territory: str) -> str:
        """stpsyr name -> DipworkPy field. Coast suffixes map to the exact
        SUBFIELD (BuS, SpN, ...) so the order pre-processor can apply the
        DATC 6.B coast rules; uncoasted names stay superfields."""
        t = territory.strip()
        sub = self._COAST_SUBFIELDS.get(t.lower())
        if sub:
            return sub
        return convert_territory(t)

    def parse_unit_type(self, unit_desc: str) -> str:
        """Parse unit type from description"""
        if unit_desc.startswith("F ") or "Fleet" in unit_desc:
            return "F"
        elif unit_desc.startswith("A ") or "Army" in unit_desc:
            return "A"
        else:
            return "A"  # Default to army

    def parse_order(self, line: str, nation: str) -> Optional[Order]:
        line = line.strip()
        if not line:
            return None
        parts = line.split()
        if len(parts) < 2:
            return None
        unit_type = parts[0]  # A or F
        order_text = " ".join(parts[1:])
        # explicit B.3.2.13/B.3.2.14 marker — must not be lost; only armies
        # can be convoyed (a fleet "(via convoy)" is corpus noise).
        via_convoy = unit_type == "A" and "(via convoy)" in order_text
        if "(via convoy)" in order_text:
            order_text = order_text.replace("(via convoy)", "").strip()

        if " S " in order_text:  # support
            lhs, support_text = order_text.split(" S ", 1)
            current = self.parse_territory_name(lhs)
            if support_text.startswith("A ") or support_text.startswith("F "):
                support_text = support_text[2:]
            tokens = support_text.split()
            if tokens and tokens[-1] == "H":  # "S tri H" == support-to-hold
                tokens = tokens[:-1]
            support_text = " ".join(tokens)
            if "-" in support_text:  # support-to-move "apu-ven"
                start, _dest = support_text.split("-", 1)
                return Order(
                    nation=nation,
                    utype=unit_type,
                    current=current,
                    order=OrderType.msup,
                    dest=self.parse_territory_name(start),
                )
            if support_text:
                return Order(
                    nation=nation,
                    utype=unit_type,
                    current=current,
                    order=OrderType.hsup,
                    dest=self.parse_territory_name(support_text),
                )
            return None

        if " C " in order_text:  # convoy — dest = convoyed unit's start
            lhs, convoy_info = order_text.split(" C ", 1)
            current = self.parse_territory_name(lhs)
            if convoy_info.startswith("A ") or convoy_info.startswith("F "):
                convoy_info = convoy_info[2:]
            dest = self.parse_territory_name(convoy_info.split("-")[0]) if "-" in convoy_info else current
            return Order(nation=nation, utype=unit_type, current=current, order=OrderType.con, dest=dest)

        tokens = order_text.split()
        if tokens and tokens[-1] == "H":  # "lon H" == explicit hold
            tokens = tokens[:-1]
        order_text = " ".join(tokens)

        if "-" in order_text:  # move "lon-pic" / "mao-spa/nc"
            start, dest = order_text.split("-", 1)
            return Order(
                nation=nation,
                utype=unit_type,
                current=self.parse_territory_name(start),
                order=OrderType.mve,
                dest=self.parse_territory_name(dest),
                via_convoy=via_convoy,
            )

        if order_text:  # bare territory == hold
            return Order(
                nation=nation, utype=unit_type, current=self.parse_territory_name(order_text), order=OrderType.hld
            )
        return None

    def parse_file(self, filename: str) -> List["TestCase"]:
        test_cases: List[TestCase] = []
        cur: Optional[TestCase] = None
        phase = Phase(orders=[], builds=[], disbands=[])
        nation = ""

        def close_phase():
            nonlocal phase
            if phase.orders or phase.builds or phase.disbands:
                assert cur is not None
                cur.phases.append(phase)
            phase = Phase(orders=[], builds=[], disbands=[])

        def close_case():
            nonlocal cur
            if cur is not None:
                close_phase()
                if cur.phases and cur.expected_results:
                    test_cases.append(cur)
                else:
                    print(f"⚠️  dropping stub/incomplete case {cur.number}. {cur.title}")
            cur = None

        with open(filename, "r") as f:
            for raw in f:
                line = raw.rstrip("\n")
                stripped = line.strip()
                if stripped.startswith("/"):  # '//' comment (lib.rs)
                    continue
                if line.startswith("# "):  # case header
                    close_case()
                    header = line[2:].strip()
                    if ". " in header:
                        num_str, title = header.split(". ", 1)
                        try:
                            cur = TestCase(number=int(num_str), title=title, phases=[], expected_results={})
                        except ValueError:
                            cur = None
                    continue
                if cur is None:
                    continue
                if not stripped:  # blank line = phase end
                    close_phase()
                    continue
                if line.startswith("    "):  # order / build / disband
                    parts = stripped.split()
                    if parts[0] == "B" and len(parts) == 3:
                        phase.builds.append((nation, parts[1], self.parse_territory_name(parts[2])))
                    elif parts[0] == "D" and len(parts) == 2:
                        phase.disbands.append(self.parse_territory_name(parts[1]))
                    else:
                        order = self.parse_order(line, nation)
                        if order:
                            phase.orders.append(order)
                    continue
                if ":" in line:  # "lon: Fleet England"
                    territory, expected = line.split(":", 1)
                    cur.expected_results[self.parse_territory_name(territory)] = expected.strip()
                    continue
                nation = self.parse_nation_name(stripped)  # nation line
        close_case()
        return test_cases

    def _board_position(self, board, o: Order):
        """The unit's ACTUAL board key for a corpus order: same nation on
        the named superfield. The board is the truth — corpus unit-type
        labels are frequently wrong ("A tri-ven" for the FLEET on Tri,
        "A rum-bul/ec" for the FLEET on Rum); the caller rewrites the
        order's utype from the board. None if no unit of that nation is
        there — the corpus order is void (DATC: order for a unit not there)."""
        want_super = _super(o.current)
        for key, unit in board.items():
            if _super(key) == want_super and unit[0] == o.nation:
                return key
        return None

    def run_test_case(self, test_case, verbose=False):
        """Returns 'PASS' | 'FAIL' | 'ERROR'."""
        from collections import Counter

        from dipworkpy.round.orchestrator import RoundRequest, round_full

        board = dict(STANDARD_START)
        dislodged = {}
        try:
            for phase in test_case.phases:
                # builds/disbands are their own (winter) blocks in the
                # files and precede the next movement block
                for terr in phase.disbands:
                    board.pop(terr, None)
                    board = {k: u for k, u in board.items() if _super(k) != terr}
                for nation, utype, terr in phase.builds:
                    board[terr] = (nation, utype)
                if not phase.orders:
                    continue
                if dislodged and all(dislodged.get(_super(o.current)) == (o.nation, o.utype) for o in phase.orders):
                    # Retreat phase: every order references a unit that
                    # was just dislodged (e.g. datc-6.f.7 'F nth-bel').
                    # Naive application, no retreat-conflict engine:
                    # retreat-move to an empty, uncontested field
                    # succeeds; everything else disbands (the unit is
                    # already off the board).
                    dest_counts = Counter(o.dest for o in phase.orders if o.order == OrderType.mve and o.dest)
                    for o in phase.orders:
                        if o.order == OrderType.mve and o.dest and o.dest not in board and dest_counts[o.dest] == 1:
                            board[o.dest] = (o.nation, o.utype)
                    dislodged = {}
                    continue
                # Board-consistent orders: relocate every corpus order to
                # the unit's ACTUAL board position (coast-exact: subfield
                # board keys carry the DATC 6.B position). Orders for units
                # that are NOT where the corpus claims are void (dropped);
                # unordered board units hold (disorder rule).
                orders2, covered = [], set()
                for o in phase.orders:
                    pos = self._board_position(board, o)
                    if pos is None:
                        continue
                    o2 = o.model_copy(update={"current": pos, "utype": board[pos][1]})
                    orders2.append(o2)
                    covered.add(pos)
                for pos, (nat, ut) in board.items():
                    if pos not in covered:
                        orders2.append(Order(nation=nat, utype=ut, current=pos, order=OrderType.hld))
                rr = round_full(
                    RoundRequest(
                        orders=orders2,
                        unit_positions={f: u for f, u in board.items()},
                        # The DATC-based corpus honours the explicit
                        # "(via convoy)" marker: Gilgamesch B.3.2.14 Satz 1.
                        switches=Switches(convoy_via_explicit=True),
                    )
                )
                board, dislodged = apply_resolution(board, rr.conflict.resolution, phase.orders)
        except Exception as e:
            print(f"! ERROR test {test_case.number} ({test_case.title}): {e}")
            return "ERROR"

        mismatches = []
        for territory, expectation in test_case.expected_results.items():
            if not expected_matches(board, territory, expectation, self.parse_nation_name):
                mismatches.append(f"{territory}: expected {expectation!r}, board has {board.get(territory)}")
        if mismatches:
            print(f"- FAIL test {test_case.number} ({test_case.title})")
            for m in mismatches:
                print(f"    {m}")
            return "FAIL"
        if verbose:
            print(f"+ PASS test {test_case.number} ({test_case.title})")
        return "PASS"

    def run_file(self, filename: str, verbose: bool = False) -> Tuple[int, int, int, int]:
        """Run every case in a file. Returns (passed, failed, errors, total)."""
        print(f"\n=== Running tests from {filename} ===")

        test_cases = self.parse_file(filename)
        print(f"Found {len(test_cases)} test cases")

        passed = failed = errors = 0
        for test_case in test_cases:
            verdict = self.run_test_case(test_case, verbose)
            if verdict == "PASS":
                passed += 1
            elif verdict == "FAIL":
                failed += 1
            else:
                errors += 1

        total = len(test_cases)
        print(f"\nResults: {passed} PASS / {failed} FAIL / {errors} ERROR (of {total})")
        return passed, failed, errors, total


def main():
    """Run all stpsyr DATC files and report PASS/FAIL/ERROR."""
    runner = StpsyrTestRunner()

    # Test files to process (relative to current directory)
    test_files = [
        "datc-6.a.txt",
        "datc-6.b.txt",
        "datc-6.c.txt",
        "datc-6.d.txt",
        "datc-6.e.txt",
        "datc-6.f.txt",
    ]

    total_passed = total_failed = total_errors = total_tests = 0

    for filename in test_files:
        path = os.path.join(BASE_DIR, filename)
        if os.path.exists(path):
            passed, failed, errors, tests = runner.run_file(path, verbose=True)
            total_passed += passed
            total_failed += failed
            total_errors += errors
            total_tests += tests
        else:
            print(f"⚠️  Test file {filename} not found")

    if total_tests == 0:
        print("❌ No test files found — path bug?")
        return 1

    print("\n=== OVERALL SUMMARY ===")
    print(f"Total: {total_passed} PASS / {total_failed} FAIL / {total_errors} ERROR (of {total_tests})")

    # Exit 0 only once nothing fails or errors (and we actually ran cases).
    if total_failed == 0 and total_errors == 0:
        print("✅ All cases PASS")
        return 0
    print(
        "⚠️  FAILs triage (2026-09-09): pre-existing coast/board-position family "
        "(split-coast board comparison gaps), plus test 32 whose expectation the "
        "corpus itself marks as differing from the DATC recommendation."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
