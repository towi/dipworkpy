#!/usr/bin/env python3
"""
Python test runner for stpsyr DATC test cases
Based on https://github.com/tckmn/stpsyr/blob/master/tests/lib.rs
"""

import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Local imports
sys.path.insert(0, '..')  # Add parent directory to path
from dipworkpy.model import Situation, Order, OrderType, Switches
from dipworkpy.conflict_game import conflict_game


@dataclass
class TestCase:
    """Represents a single test case"""
    number: int
    title: str
    orders: List[Order]
    expected_results: Dict[str, str]  # territory -> expected unit state


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
            "Turkey": "Tu"
        }
        return name_map.get(name, name[:2].upper())

    def parse_territory_name(self, territory: str) -> str:
        """Convert stpsyr territory names to DipworkPy notation"""
        # Common territory mappings
        territory_map = {
            "lon": "Lon", "pic": "Pic", "rom": "Rom", "tun": "Tun",
            "lvp": "Lvp", "iri": "Iri", "kie": "Kie", "ruh": "Ruh",
            "ven": "Ven", "tyr": "Tyr", "tri": "Tri", "adr": "Adr",
            "bud": "Bud", "vie": "Vie", "nth": "NTH", "edi": "Edi",
            "bel": "Bel", "con": "Con", "bul": "Bul", "smy": "Smy",
            "ank": "Ank", "apu": "Apu", "nap": "Nap", "mun": "Mun",
            "war": "War", "gal": "Gal", "sil": "Sil", "ber": "Ber",
            "pru": "Pru", "ser": "Ser", "alb": "Alb", "eng": "ENG",
            "bre": "Bre", "par": "Par", "spa": "Spa", "mar": "Mar",
            "pie": "Pie", "tus": "Tus", "mos": "Mos", "sev": "Sev",
            "ukr": "Ukr", "rum": "Rum", "bla": "BLA", "arm": "Arm",
            "syr": "Syr", "mad": "MAD", "hel": "HEL", "bal": "BAL"
        }
        return territory_map.get(territory.lower(), territory.capitalize())

    def parse_unit_type(self, unit_desc: str) -> str:
        """Parse unit type from description"""
        if unit_desc.startswith('F ') or 'Fleet' in unit_desc:
            return 'F'
        elif unit_desc.startswith('A ') or 'Army' in unit_desc:
            return 'A'
        else:
            return 'A'  # Default to army

    def parse_order(self, line: str, nation: str) -> Optional[Order]:
        """Parse a single order line"""
        line = line.strip()
        if not line:
            return None

        # Remove leading whitespace and parse
        parts = line.split()
        if len(parts) < 2:
            return None

        unit_type = parts[0]  # A or F
        order_text = ' '.join(parts[1:])

        # Handle convoy notation "(via convoy)" - remove for now
        if '(via convoy)' in order_text:
            order_text = order_text.replace('(via convoy)', '').strip()

        # Parse different order formats
        if ' S ' in order_text:  # Support
            # Format: "rom S A apu-ven" or "tri S tri"
            current_dest = order_text.split(' S ', 1)
            current = self.parse_territory_name(current_dest[0])
            support_text = current_dest[1]

            # Remove unit type prefix if present
            if support_text.startswith('A ') or support_text.startswith('F '):
                support_text = support_text[2:]

            if '-' in support_text:
                # Support to move: "apu-ven"
                support_parts = support_text.split('-')
                if len(support_parts) == 2:
                    dest = self.parse_territory_name(support_parts[1])
                    return Order(nation=nation, utype=unit_type, current=current,
                               order=OrderType.msup, dest=dest)
            else:
                # Support to hold: "tri" or "tri H"
                hold_target = support_text.strip().split()[-1]  # Get last part
                if hold_target and hold_target != 'H':
                    dest = self.parse_territory_name(hold_target)
                    return Order(nation=nation, utype=unit_type, current=current,
                               order=OrderType.hsup, dest=dest)

        elif ' C ' in order_text:  # Convoy
            # Format: "nth C F lon-bel" or "adr C A tri-tri"
            convoy_parts = order_text.split(' C ', 1)
            current = self.parse_territory_name(convoy_parts[0])

            # Extract the army being convoyed for destination
            convoy_info = convoy_parts[1]
            if convoy_info.startswith('A ') or convoy_info.startswith('F '):
                convoy_info = convoy_info[2:]  # Remove unit type

            # Get the army's name for xref
            if '-' in convoy_info:
                army_dest = convoy_info.split('-')[0]
                dest = self.parse_territory_name(army_dest)
            else:
                dest = current

            return Order(nation=nation, utype=unit_type, current=current,
                       order=OrderType.con, dest=dest)

        elif '-' in order_text and not order_text.count('-') > 1:  # Simple move
            # Format: "lon-pic" or "ven-tyr"
            move_parts = order_text.split('-')
            if len(move_parts) == 2:
                current = self.parse_territory_name(move_parts[0])
                dest = self.parse_territory_name(move_parts[1])
                return Order(nation=nation, utype=unit_type, current=current,
                           order=OrderType.mve, dest=dest)
        else:
            # Simple territory name - hold order
            current = self.parse_territory_name(order_text)
            return Order(nation=nation, utype=unit_type, current=current,
                       order=OrderType.hld)

        return None

    def parse_file(self, filename: str) -> List[TestCase]:
        """Parse a single stpsyr test file"""
        test_cases = []
        current_test_num = 0
        current_title = ""
        current_nation = ""
        current_orders = []
        current_expected = {}
        collecting_orders = False
        collecting_results = False

        with open(filename, 'r') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            if line.startswith('# '):  # Test case header
                # Save previous test case if complete
                if current_test_num > 0 and current_orders and current_expected:
                    test_case = TestCase(
                        number=current_test_num,
                        title=current_title,
                        orders=current_orders.copy(),
                        expected_results=current_expected.copy()
                    )
                    test_cases.append(test_case)

                # Reset for new test case
                current_orders = []
                current_expected = {}
                collecting_orders = False
                collecting_results = False

                # Parse header: "# 1. Moving to an area that is not a neighbor"
                header = line[2:].strip()
                if '. ' in header:
                    num_str, title = header.split('. ', 1)
                    try:
                        current_test_num = int(num_str)
                        current_title = title
                        collecting_orders = True
                    except ValueError:
                        pass

            elif line and not line.startswith(' ') and ':' in line:
                # Expected result line: "lon: Fleet England"
                collecting_orders = False
                collecting_results = True
                territory, expected = line.split(': ', 1)
                territory = self.parse_territory_name(territory.strip())
                current_expected[territory] = expected.strip()

            elif line and not line.startswith(' ') and not line.startswith('#') and collecting_orders:
                # Nation line: "England"
                current_nation = self.parse_nation_name(line.strip())

            elif line.startswith('    ') and collecting_orders and current_nation:
                # Order line: "    F lon-pic"
                order = self.parse_order(line, current_nation)
                if order:
                    current_orders.append(order)

            i += 1

        # Handle last test case
        if current_test_num > 0 and current_orders and current_expected:
            test_case = TestCase(
                number=current_test_num,
                title=current_title,
                orders=current_orders.copy(),
                expected_results=current_expected.copy()
            )
            test_cases.append(test_case)

        return test_cases

    def run_test_case(self, test_case: TestCase, verbose: bool = False) -> bool:
        """Run a single test case and verify results"""
        if verbose:
            print(f"\n=== Test {test_case.number}: {test_case.title} ===")

        try:
            # Create situation
            situation = Situation(orders=test_case.orders)

            if verbose:
                print("Orders:")
                for order in test_case.orders:
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
        if os.path.exists(filename):
            passed, tests = runner.run_file(filename, verbose=True)
            total_passed += passed
            total_tests += tests
        else:
            print(f"⚠️  Test file {filename} not found")

    print(f"\n=== OVERALL SUMMARY ===")
    print(f"Total tests executed: {total_passed}/{total_tests}")

    if total_passed == total_tests:
        print("✅ All tests executed successfully!")
        return 0
    else:
        print("⚠️  Some tests had issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())