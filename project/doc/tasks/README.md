# Implementation Tasks

## TESTEX: Test Expansion - DipNet Dataset Runner

Run the DipworkPy conflict resolution engine against 33,279 real games from the diplomacy/research dataset.

| Task | Description | Status | File |
|------|-------------|--------|------|
| [TESTEX-001](TASK-TESTEX-001.md) | Notation mapping module | Done | `test_data_pipeline/mappings.py` |
| [TESTEX-002](TASK-TESTEX-002.md) | JSONL phase parser | Done | `test_data_pipeline/dipnet_parser.py` |
| [TESTEX-003](TASK-TESTEX-003.md) | Test evaluator | Done | `test_data_pipeline/evaluator.py` |
| [TESTEX-004](TASK-TESTEX-004.md) | CLI script | Done | `test_data_pipeline/run_dipnet_tests.py` |
| [TESTEX-005](TASK-TESTEX-005.md) | Integration & docs | Done | Makefile, CLAUDE.md, TEST_EXPANSION.md |

## Current Results (100 games, 1,602 test cases)

```
  + PASS:             307 ( 19.2%)
  - FAIL:             466 ( 29.1%)
  ! ERROR:              0 (  0.0%)
  ? INCONCLUSIVE:     829 ( 51.7%)
    (convoy: 197, void: 632)
```
