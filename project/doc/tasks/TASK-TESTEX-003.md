# TASK-TESTEX-003: Test Evaluator

**Status:** Done
**File:** `project/test_data_pipeline/evaluator.py`

## Description

Run DwpcrTestCases through conflict_game() and compare results. Pure functions, no shared state.

## Contents

- `TestResult` enum: PASS(+), FAIL(-), ERROR(!), INCONCLUSIVE(?)
- `EvalResult` dataclass: test_id, result, reason, test_case, actual output, diffs
- `evaluate_test_case()`: pure function, runs one test case
- `format_failure()`: format full failure report in DipworkPy notation
- `ResultSummary`: aggregated statistics with format_summary()

## Key Decisions

- Data isolation: evaluate_test_case is pure (no shared mutable state)
- Void results -> INCONCLUSIVE without running engine
- Convoy tests: run engine, if differs -> INCONCLUSIVE (not FAIL)
- format_failure shows full situation for --with-failures output
- Comparison by (nation, utype, current) key, comparing only succeeds and dislodged
