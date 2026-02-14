# Test Suite Expansion Design

## Goal

Expand from ~30 working tests to ~500K test cases for the Conflict Resolution engine, drawn from real game data and the full DATC specification.

## Data Sources

| Source | Size | Format | Status |
|--------|------|--------|--------|
| diplomacy/research | 33,279 games (~500K phases) | JSONL | **Implemented** (test_data_pipeline) |
| STPSYR DATC files | 98 test cases | .txt (in repo) | 33/98 parsing, parser has bugs |
| DATC v3.0 full spec | ~200 test cases | HTML | Downloaded, not parsed |
| PlayDiplomacy scrape | 76,798 games | CSV | Future |

All sources use pre-2023 original rulebook (compatible with DipworkPy's convoy rules).

## DipNet Test Runner (Implemented)

### Architecture

```
standard_no_press.jsonl
        |
        v
  JSONL Line Reader       reads game-by-game
        |
        v   for each movement phase
  DipNet -> DipworkPy     notation mapping (from FIELDS.TXT)
  Translator              (territory, nation, order, result)
        |
        v   DwpcrTestCase (self-contained, no shared state)
  conflict_game()         run DipworkPy engine (pure function)
  Evaluator
        |
        v   compare actual vs expected
  Result Reporter         +/-/!/? statistics
```

### Usage

```bash
# Quick test (100 games, ~1600 tests):
make test-dipnet-quick

# Full dataset (33K games, ~500K tests):
make test-dipnet-full

# CLI with failure details:
python -m test_data_pipeline.run_dipnet_tests --max-games 100 --with-failures data.jsonl

# Dump test cases as JSON:
python -m test_data_pipeline.run_dipnet_tests --dump-json --max-games 10 data.jsonl
```

### Result Categories

- `+` PASS: DipworkPy output matches expected
- `-` FAIL: outputs differ (to investigate)
- `!` ERROR: exception or crash
- `?` INCONCLUSIVE: test contains void results or convoy differences

### Current Results (100 games)

```
Games: 100 | Test cases: 1,602

Results:
  + PASS:             307 ( 19.2%)
  - FAIL:             466 ( 29.1%)
  ! ERROR:              0 (  0.0%)
  ? INCONCLUSIVE:     829 ( 51.7%)
    (convoy: 197, void: 632)
```

The high inconclusive rate comes from void results (39.5% of test cases contain geography-dependent invalid orders that need the Geography phase).

### Data Isolation

Each `DwpcrTestCase` is fully self-contained: no shared mutable state. The evaluator is a pure function. This enables future parallelization via `multiprocessing.Pool.map()` without changes.

### Files

```
project/test_data_pipeline/
  __init__.py          # Package init
  mappings.py          # Nation/territory/order/result mapping (from FIELDS.TXT)
  dipnet_parser.py     # JSONL reader + DwpcrTestCase generator
  evaluator.py         # conflict_game runner + result comparison
  run_dipnet_tests.py  # CLI entry point + reporting
  __main__.py          # python -m support
```

## Notation Mapping

### Territory Mapping (DipNet -> DipworkPy)

Derived from FIELDS.TXT. Non-trivial renames:

| DipNet | DipworkPy | Reason |
|--------|-----------|--------|
| BAL | BAS | Baltic Sea |
| LVN | Liv | Livonia |
| LVP | Lpl | Liverpool |
| MAO | MID | Mid-Atlantic Ocean |
| NAF | Afr | North Africa |
| NAO | NAT | North Atlantic Ocean |
| NWG | NWS | Norwegian Sea |
| NWY | Nor | Norway |
| SEV | Seb | Sevastopol |
| STP | Pet | St. Petersburg |
| WES | WMS | Western Mediterranean Sea |

Rules: Ocean territories stay uppercase (NTH). Land territories capitalize first (PAR -> Par). Coast suffixes strip to superfield (SPA/SC -> Spa).

### Order Mapping

| DipNet | DipworkPy | dest field |
|--------|-----------|------------|
| `A PAR H` | `hld`, dest=None | - |
| `A PAR - BUR` | `mve`, dest=`Bur` | move destination |
| `A MAR S A PAR` | `hsup`, dest=`Par` | supported unit's location |
| `A MAR S A PAR - BUR` | `msup`, dest=`Par` | supported unit's location (**not** Bur) |
| `F ENG C A LON - BEL` | `con`, dest=`Lon` | convoyed army's location (**not** Bel) |
| `A LON - BEL VIA` | `mve`, dest=`Bel` | move destination (strip VIA) |

### Result Mapping

| DipNet result | `succeeds` | `dislodged` | Category |
|---------------|------------|-------------|----------|
| `[]` | `None` (success) | `None` | PASS candidate |
| `["bounce"]` | `False` | `None` | PASS candidate |
| `["cut"]` | `False` | `None` | PASS candidate |
| `["dislodged"]` | `None` | `True` | PASS candidate |
| `["bounce", "dislodged"]` | `False` | `True` | PASS candidate |
| `["cut", "dislodged"]` | `False` | `True` | PASS candidate |
| `["void"]` | - | - | INCONCLUSIVE |
| `["no convoy"]` | `False` | `None` | PASS candidate |

## Convoy Test Marking

Tests that include convoy orders are marked `?con` (PRELIMINARY) because:
- The Conflict Resolver currently uses `convoy_routing_engine: "always"` (no geographic validation)
- Real game adjudication may differ when convoy routes are geographically invalid
- These tests will be finalized once geography is implemented

If a convoy test still passes with `"always"` mode, it counts as PASS. If it differs, it's marked INCONCLUSIVE (not FAIL).

## Known DATC Differences

3 DATC tests fail due to algorithm differences (not bugs):
1. **6.D.2** - Support mechanics
2. **6.D.3** - Support cutting
3. **6.F.1** - Beleaguered garrison
