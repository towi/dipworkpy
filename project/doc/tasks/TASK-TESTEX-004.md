# TASK-TESTEX-004: CLI Script

**Status:** Done
**File:** `project/test_data_pipeline/run_dipnet_tests.py`

## Description

CLI entry point for running DipNet tests with argparse, progress indicator, and reporting.

## Usage

```bash
python -m test_data_pipeline.run_dipnet_tests [OPTIONS] JSONL_FILE

Options:
  --max-games N       Stop after N games
  --with-failures     Print full situation for FAIL cases
  --verbose           Print full situation for all non-PASS cases
  --dump-json         Stream test cases as JSON (no evaluation)
```

## Key Decisions

- Progress indicator every 1000 tests (on stderr)
- --with-failures prints complete orders + expected + actual + diffs in DipworkPy notation
- --verbose is superset of --with-failures (also shows INCONCLUSIVE and ERROR)
- Exit code 1 if any failures or errors
- --dump-json streams JSONL for piping/saving
