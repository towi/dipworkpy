# STPSYR Test Cases

This directory contains DATC (Diplomacy Adjudication Test Cases) test files from the [stpsyr](https://github.com/tckmn/stpsyr) project - a Rust Diplomacy adjudicator.

## Files

- **`lib.rs`** - Original Rust test runner (for reference)
- **`datc-6.a.txt`** - Basic checks (12 test cases)
- **`datc-6.b.txt`** - Coastal issues (10 test cases)
- **`datc-6.c.txt`** - Circular movement (5 test cases)
- **`datc-6.d.txt`** - Support mechanics (35 test cases)
- **`datc-6.e.txt`** - Convoy operations (21 test cases)
- **`datc-6.f.txt`** - Beleaguered garrison (15 test cases)

**Total: ~98 DATC test cases**

## File Format

The stpsyr format uses a structured text format:

```
# 1. Test case title

Nation1
    Unit1 order1
    Unit2 order2
Nation2
    Unit3 order3

expected_territory1: expected_state1
expected_territory2: expected_state2
```

## Python Test Runners

### Simple Test Runner
**File**: `test_stpsyr_simple.py`
- Tests basic scenarios (bounce, multi-unit conflicts)
- Hand-coded test cases for verification
- **Usage**: `make test-stpsyr`

### Full Test Runner
**File**: `stpsyr_test_runner.py`
- Parses all stpsyr test files automatically
- Converts stpsyr notation to DipworkPy format
- Handles complex multi-phase scenarios
- **Usage**: `make test-stpsyr-full` (experimental)

## Territory Name Mapping

Stpsyr uses 3-letter lowercase codes, DipworkPy uses 3-letter mixed case:

| Stpsyr | DipworkPy | Territory |
|--------|-----------|-----------|
| `lon`  | `Lon`     | London    |
| `nth`  | `NTH`     | North Sea |
| `vie`  | `Vie`     | Vienna    |
| `bre`  | `Bre`     | Brest     |

## Nation Name Mapping

| Stpsyr      | DipworkPy | Nation  |
|-------------|-----------|---------|
| `England`   | `En`      | England |
| `France`    | `Fr`      | France  |
| `Germany`   | `Ge`      | Germany |
| `Austria`   | `Au`      | Austria |
| `Italy`     | `It`      | Italy   |
| `Russia`    | `Ru`      | Russia  |
| `Turkey`    | `Tu`      | Turkey  |

## Current Status

- ✅ **Test files downloaded** - All 6 DATC section files
- ✅ **Basic parser working** - Can read stpsyr format
- ✅ **Simple tests passing** - Bounce scenarios work correctly
- ⚠️ **Complex cases** - Multi-phase scenarios need parser improvements
- ❌ **Result verification** - Expected vs actual comparison not implemented

## Integration

The STPSYR tests are integrated into the main build system:

```bash
make check          # Includes simple STPSYR tests
make test-stpsyr    # Run simple STPSYR tests
make test-stpsyr-full  # Run experimental full parser
```

These tests provide additional validation beyond our core DATC test suite and help ensure compatibility with standard Diplomacy adjudication.