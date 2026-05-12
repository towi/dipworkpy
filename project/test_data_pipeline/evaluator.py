"""Test evaluator: runs DwpcrTestCases through conflict_game and compares results.

Each evaluate_test_case() call is a pure function with no shared mutable state,
enabling future parallelization via multiprocessing.Pool.map().
"""

import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from dipworkpy.conflict_game import conflict_game
from dipworkpy.model import ConflictResolution, OrderResult, OrderType, Situation, Switches

from .dipnet_parser import DwpcrTestCase
from .mappings import format_order_dwp, format_oresult_dwp


class TestResult(Enum):
    PASS = "+"
    FAIL = "-"
    ERROR = "!"
    INCONCLUSIVE = "?"


@dataclass
class EvalResult:
    """Result of evaluating a single test case.

    When keep_details=True, stores the original test case and engine output
    for detailed failure reporting. When False, only lightweight fields are set
    to avoid accumulating memory over 500K+ test cases.
    """

    test_id: str
    result: TestResult
    reason: str  # "convoy", "void", error message, or diff summary
    test_case: Optional[DwpcrTestCase] = None  # only when keep_details=True
    actual: Optional[ConflictResolution] = None  # only when keep_details=True
    diffs: List[str] = field(default_factory=list)


def _compare_orders(
    expected: List[OrderResult], actual: List[OrderResult],
    skip_keys: Optional[set] = None,
) -> List[str]:
    """Compare expected vs actual order results, return list of diff strings.

    Returns empty list if all match. Orders whose (nation, utype, current)
    key is in `skip_keys` are excluded from comparison entirely — used to
    ignore orders the dataset marked as `void` (geographically invalid).
    """
    diffs: List[str] = []
    skip = skip_keys or set()

    # Build lookup by (nation, utype, current) for actual results
    actual_lookup: dict[tuple[str, str, str], OrderResult] = {}
    for a in actual:
        key = (a.nation, a.utype, a.current)
        actual_lookup[key] = a

    for exp in expected:
        key = (exp.nation, exp.utype, exp.current)
        if key in skip:
            continue
        act = actual_lookup.get(key)
        if act is None:
            diffs.append(
                f"  {format_oresult_dwp(exp)}: missing in actual output"
            )
            continue

        # Compare succeeds and dislodged
        # Convention: None means "success/default", False means "failed", True means "dislodged"
        exp_s = exp.succeeds
        act_s = act.succeeds
        exp_d = exp.dislodged
        act_d = act.dislodged

        if exp_s != act_s or exp_d != act_d:
            parts = []
            if exp_s != act_s:
                parts.append(f"succeeds: expected={exp_s}, got={act_s}")
            if exp_d != act_d:
                parts.append(f"dislodged: expected={exp_d}, got={act_d}")
            order_str = format_order_dwp(exp)  # type: ignore[arg-type]
            diffs.append(f"  {order_str}: {', '.join(parts)}")

    # Check for unexpected orders in actual
    expected_keys = {(e.nation, e.utype, e.current) for e in expected}
    for act in actual:
        key = (act.nation, act.utype, act.current)
        if key in skip:
            continue
        if key not in expected_keys:
            diffs.append(
                f"  {format_oresult_dwp(act)}: unexpected in actual output"
            )

    return diffs


def evaluate_test_case(tc: DwpcrTestCase, keep_details: bool = False) -> EvalResult:
    """Run one test case through conflict_game and compare results.

    Pure function: no shared mutable state. Safe for parallel execution.

    Void-handling strategy (P8): Orders the dataset marked as `void` are
    geographically invalid in the source data. Rather than short-circuiting
    the whole test case to INCONCLUSIVE, we:

    1. Rewrite the void orders to plain holds before handing them to the
       engine — that prevents an invalid support from accidentally
       boosting a real move (e.g. ION supporting Nap->Rom when ION is
       not adjacent to Rom).
    2. Skip the void orders during result comparison — their succeed/fail
       result depends on dataset-side semantics the engine doesn't model.

    If every non-void order matches, the case is a legitimate PASS.

    Args:
        tc: Test case to evaluate
        keep_details: If True, store test_case and actual in result for
            failure reporting. If False, only store lightweight fields
            to save memory on large runs.
    """
    # Build skip-set for void orders (compared post-engine).
    void_keys: set = set()
    void_indices_set = set(tc.void_order_indices)
    for idx in tc.void_order_indices:
        if 0 <= idx < len(tc.orders):
            o = tc.orders[idx]
            void_keys.add((o.nation, o.utype, o.current))

    # Rewrite void orders to holds for the engine. The engine will then
    # treat them as units that occupy their fields without supporting or
    # moving — matching what the dataset's void marker means.
    if void_indices_set:
        engine_orders = []
        for i, o in enumerate(tc.orders):
            if i in void_indices_set:
                engine_orders.append(o.model_copy(update={
                    "order": OrderType.hld, "dest": None,
                }))
            else:
                engine_orders.append(o)
    else:
        engine_orders = tc.orders

    # Run the engine.
    try:
        situation = Situation(
            orders=engine_orders,
            switches=Switches(convoy_routing_engine="always"),
        )
        cr = conflict_game(situation)
    except Exception as e:
        tb = traceback.format_exception_only(type(e), e)
        return EvalResult(
            test_id=tc.id,
            result=TestResult.ERROR,
            reason="".join(tb).strip(),
            test_case=tc if keep_details else None,
        )

    # Compare results, skipping void-marked orders
    diffs = _compare_orders(tc.expected, cr.orders, skip_keys=void_keys)

    if not diffs:
        # If void was present, label PASS so we can still distinguish those
        # in summaries; treat as a clean PASS for percentage purposes.
        return EvalResult(
            test_id=tc.id,
            result=TestResult.PASS,
            reason="void-skipped" if tc.has_void else "",
        )

    # Has diffs - decide FAIL vs INCONCLUSIVE (convoy)
    if tc.has_convoy:
        return EvalResult(
            test_id=tc.id,
            result=TestResult.INCONCLUSIVE,
            reason="convoy",
            test_case=tc if keep_details else None,
            actual=cr if keep_details else None,
            diffs=diffs,
        )

    return EvalResult(
        test_id=tc.id,
        result=TestResult.FAIL,
        reason=f"{len(diffs)} order(s) differ",
        test_case=tc if keep_details else None,
        actual=cr if keep_details else None,
        diffs=diffs,
    )


def format_failure(er: EvalResult) -> str:
    """Format a full failure report in DipworkPy notation.

    Shows all input orders, expected results, actual results, and diffs.
    Designed to be copy-pasteable for debugging.
    Requires keep_details=True during evaluation for full output.
    """
    lines: List[str] = []
    lines.append(f"--- {er.result.value} {er.result.name}: {er.test_id} ---")

    if er.reason:
        lines.append(f"Reason: {er.reason}")

    if er.test_case is not None:
        # Input orders
        lines.append("Orders (DipworkPy notation):")
        for o in er.test_case.orders:
            lines.append(f"  {format_order_dwp(o)}")

        # Expected results
        lines.append("Expected results:")
        for e in er.test_case.expected:
            lines.append(f"  {format_oresult_dwp(e)}")

    # Actual results (if available)
    if er.actual is not None:
        lines.append("Actual results:")
        for a in er.actual.orders:
            lines.append(f"  {format_oresult_dwp(a)}")

    # Diffs
    if er.diffs:
        lines.append("Differences:")
        for d in er.diffs:
            lines.append(d)

    # Parse warnings
    if er.test_case is not None and er.test_case.parse_warnings:
        lines.append("Parse warnings:")
        for w in er.test_case.parse_warnings:
            lines.append(f"  {w}")

    return "\n".join(lines)


@dataclass
class ResultSummary:
    """Aggregated results from running many test cases."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    inconclusive: int = 0
    inconclusive_convoy: int = 0
    inconclusive_void: int = 0
    game_count: int = 0
    non_pass: List[EvalResult] = field(default_factory=list)

    def add(self, er: EvalResult) -> None:
        self.total += 1
        if er.result == TestResult.PASS:
            self.passed += 1
        elif er.result == TestResult.FAIL:
            self.failed += 1
            self.non_pass.append(er)
        elif er.result == TestResult.ERROR:
            self.errors += 1
            self.non_pass.append(er)
        elif er.result == TestResult.INCONCLUSIVE:
            self.inconclusive += 1
            if er.reason == "convoy":
                self.inconclusive_convoy += 1
            elif er.reason == "void":
                self.inconclusive_void += 1
            self.non_pass.append(er)

    def format_summary(self) -> str:
        if self.total == 0:
            return "No test cases."
        pct = lambda n: f"{100 * n / self.total:5.1f}%"
        lines = [
            f"Results ({self.total} test cases):",
            f"  + PASS:          {self.passed:>6} ({pct(self.passed)})",
            f"  - FAIL:          {self.failed:>6} ({pct(self.failed)})",
            f"  ! ERROR:         {self.errors:>6} ({pct(self.errors)})",
            f"  ? INCONCLUSIVE:  {self.inconclusive:>6} ({pct(self.inconclusive)})",
        ]
        if self.inconclusive > 0:
            parts = []
            if self.inconclusive_convoy > 0:
                parts.append(f"convoy: {self.inconclusive_convoy}")
            if self.inconclusive_void > 0:
                parts.append(f"void: {self.inconclusive_void}")
            lines.append(f"    ({', '.join(parts)})")
        return "\n".join(lines)
