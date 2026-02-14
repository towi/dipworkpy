# Test Suite Expansion Design

## Goal

Expand from ~30 working tests to ~3000-5000 test cases for the Conflict Resolution engine, drawn from real game data and the full DATC specification.

## Data Sources

| Source | Size | Format | Status |
|--------|------|--------|--------|
| STPSYR DATC files | 98 test cases | .txt (in repo) | 33/98 parsing, parser has bugs |
| DATC v3.0 full spec | ~200 test cases | HTML | To download |
| diplomacy/research | 156,468 games | JSONL | To download |
| PlayDiplomacy scrape | 76,798 games | CSV | Future |

All sources use pre-2023 original rulebook (compatible with DipworkPy's convoy rules).

## Convoy Test Marking

Tests that include convoy orders (`con`, or convoy-dependent `mve`) are marked `?con` (PRELIMINARY) because:
- The Conflict Resolver currently uses `convoy_routing_engine: "always"` (no geographic validation)
- Real game adjudication may differ when convoy routes are geographically invalid
- These tests will be finalized once geography is implemented

In JSON test files: `"convoy": true` flag. In test IDs: `?con_` prefix.
In pytest: `pytest.mark.xfail(reason="convoy geography not implemented")` or collected into separate `*_convoy_preliminary.json` files.

## Notation Mapping

### diplomacy/research format → DipworkPy

**Nations:**
| diplomacy lib | DipworkPy |
|---|---|
| AUSTRIA | Au |
| ENGLAND | En |
| FRANCE | Fr |
| GERMANY | Ge |
| ITALY | It |
| RUSSIA | Ru |
| TURKEY | Tu |

**Territories:** diplomacy lib uses ALL-CAPS 3-letter codes.
- Land territories: `PAR` → `Par` (capitalize first letter only)
- Sea territories: `NTH` → `NTH` (keep all-caps)
- Coasts: `SPA/NC` → `SpN` or strip to `Spa` (conflict resolution uses superfields)

**Orders:**
| diplomacy lib | DipworkPy | dest field |
|---|---|---|
| `A PAR H` | `hld`, dest=None | - |
| `A PAR - BUR` | `mve`, dest=`Bur` | move destination |
| `A MAR S A PAR` | `hsup`, dest=`Par` | supported unit's location |
| `A MAR S A PAR - BUR` | `msup`, dest=`Par` | supported unit's location (**not** Bur) |
| `F ENG C A LON - BEL` | `con`, dest=`Lon` | convoyed army's location (**not** Bel) |
| `A LON - BEL VIA` | `mve`, dest=`Bel` | move destination (strip VIA) |

**Results:**
| diplomacy lib | DipworkPy `succeeds` | `dislodged` |
|---|---|---|
| `[]` | `None` (success) | `None` |
| `["bounce"]` | `False` | `None` |
| `["void"]` | skip phase entirely | - |
| `["cut"]` | `False` | `None` |
| `["dislodged"]` | depends on order | `True` |
| `["no convoy"]` / `["disrupted"]` | `False` | `None` |

Phases containing `void` results are skipped (geography-dependent, untestable without geography service).

## Sampling Strategy

From ~156K games with ~15-30 movement phases each (~2-4M total phases):

| Category | Target count | Selection criteria |
|----------|-------------|-------------------|
| Peaceful | ~500 | All moves succeed |
| Bounces | ~1000 | At least one bounce |
| Support cuts | ~1000 | At least one cut support |
| Dislodges | ~500 | At least one dislodge |
| Convoy (?con) | ~200 | Any convoy order present |
| Complex | ~300 | Multiple mechanisms (bounce + dislodge + cut) |
| Small unit count | ~500 | 2-8 units total (easier debugging) |

Prefer diversity: max ~3 phases per game to avoid overrepresenting one game's patterns.

## Validation Pipeline

1. **Parse**: Convert external format → DipworkPy JSON
2. **Run**: Execute `conflict_game()` on each test case
3. **Compare**: Match against expected results from the data source
4. **Categorize**: MATCH (commit) / MISMATCH (investigate) / ERROR (engine bug)
5. **Mark convoys**: Flag any test with convoy orders as `?con`

Expected match rate: ~80-90%. Mismatches mainly from:
- `convoy_routing_engine: "always"` differences
- 3 known DATC algorithm issues (6.D.2, 6.D.3, 6.F.1)
- Edge cases in result interpretation

## Generated Test Format

Follows existing `testdata.json` pattern:
```json
[
  {
    "id": "research_game12345_S1901M",
    "convoy": false,
    "orders": [
      {"nation": "Au", "utype": "A", "current": "Vie", "order": "mve", "dest": "Tri"}
    ],
    "order_results": [
      {"nation": "Au", "utype": "A", "current": "Vie", "order": "mve", "dest": "Tri",
       "succeeds": null, "dislodged": null}
    ],
    "pattfields": []
  }
]
```

## File Layout

```
testdata/
  diplomacy-research/     # Downloaded JSONL dataset
    README.md
  datc-v3/                # Downloaded DATC v3.0 spec
    README.md

project/
  test_data_pipeline/     # Conversion scripts
    mappings/             # Territory, nation, order mapping tables
    downloaders/          # Data download scripts
    parsers/              # Format-specific parsers
    generators/           # Test case generation + filtering + validation
  tests/
    generated/            # Generated JSON test files (committed)
    test_generated.py     # Parametrized pytest runner
```
