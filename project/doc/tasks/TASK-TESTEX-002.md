# TASK-TESTEX-002: JSONL Phase Parser

**Status:** Done
**File:** `project/test_data_pipeline/dipnet_parser.py`

## Description

Read standard_no_press.jsonl (one game per line), extract movement phases, and translate them into DwpcrTestCase objects.

## Contents

- `DwpcrTestCase`: dataclass holding orders, expected results, convoy/void flags, game/phase IDs
- `parse_movement_phase()`: parse one movement phase into a DwpcrTestCase
- `parse_game_line()`: parse one JSONL line (one game) into list of DwpcrTestCase
- `stream_test_cases()`: streaming iterator over all test cases

## Key Decisions

- Each movement phase is self-contained (results inline, no phase pairs needed)
- Streaming API to avoid loading entire 2.7GB file into memory
- has_convoy detected by checking for ` C ` or ` VIA` in order strings
- has_void detected by checking for "void" in result lists
- Test ID format: "{game_id}_{phase_name}"
