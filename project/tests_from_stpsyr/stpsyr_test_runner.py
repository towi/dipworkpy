#!/usr/bin/env python3
"""
Python test runner for stpsyr DATC test cases
Based on https://github.com/tckmn/stpsyr/blob/master/tests/lib.rs
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Local imports — must stay below the sys.path.insert so project/ resolves.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))  # project/ on sys.path
from dipworkpy.model import Situation, Order, OrderType  # noqa: E402
from dipworkpy.conflict_game import conflict_game  # noqa: E402
from test_data_pipeline.mappings import convert_territory  # noqa: E402


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

    def parse_territory_name(self, territory: str) -> str:
        """stpsyr name -> DipworkPy superfield. Coast suffixes collapse
        (engine and board are superfield-only; see Task-10 bucket B)."""
        return convert_territory(territory.strip())

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

    def run_test_case(self, test_case: TestCase, verbose: bool = False) -> bool:
        """Run a single test case and verify results"""
        if verbose:
            print(f"\n=== Test {test_case.number}: {test_case.title} ===")

        try:
            # NOTE: Task-6 stopgap. The runner is fully rewritten in Task 7 to
            # step through every phase; until then we exercise the first
            # movement phase only so the standalone script stays runnable.
            orders = test_case.phases[0].orders if test_case.phases else []
            situation = Situation(orders=orders)

            if verbose:
                print("Orders:")
                for order in orders:
                    print(f"  {order.__log__()}")

            # Run conflict resolution
            result = conflict_game(situation)

            if verbose:
                print("Expected results:")
                for territory, expected in test_case.expected_results.items():
                    print(f"  {territory}: {expected}")

                print("Actual results:")
                for order_result in result.orders:
                    unit_desc = f"{order_result.utype} {order_result.nation}"
                    if order_result.dislodged:
                        unit_desc += " (dislodged)"
                    print(f"  {order_result.current}: {unit_desc}")

            # For now, just verify it runs without crashing
            # TODO: Implement proper result verification
            print(f"✅ Test {test_case.number} executed (result verification not implemented)")
            return True

        except Exception as e:
            print(f"❌ Test {test_case.number} failed with error: {e}")
            return False

    def run_file(self, filename: str, verbose: bool = False) -> Tuple[int, int]:
        """Run all test cases in a file"""
        print(f"\n=== Running tests from {filename} ===")

        test_cases = self.parse_file(filename)
        print(f"Found {len(test_cases)} test cases")

        passed = 0
        total = len(test_cases)

        for test_case in test_cases:
            if self.run_test_case(test_case, verbose):
                passed += 1

        print(f"\nResults: {passed}/{total} tests executed successfully")
        return passed, total


def main():
    """Main function to run all stpsyr tests"""
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

    total_passed = 0
    total_tests = 0

    for filename in test_files:
        path = os.path.join(BASE_DIR, filename)
        if os.path.exists(path):
            passed, tests = runner.run_file(path, verbose=True)
            total_passed += passed
            total_tests += tests
        else:
            print(f"⚠️  Test file {filename} not found")

    if total_tests == 0:
        print("❌ No test files found — path bug?")
        return 1

    print("\n=== OVERALL SUMMARY ===")
    print(f"Total tests executed: {total_passed}/{total_tests}")

    if total_passed == total_tests:
        print("✅ All tests executed successfully!")
        return 0
    else:
        print("⚠️  Some tests had issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
