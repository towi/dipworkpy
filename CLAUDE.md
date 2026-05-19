# dipworkpy

## Strict Rules

- The `./pas/` directory is **private and confidential**. NEVER describe its contents, reference it in documentation,
  mention it in commits, or include it in git. It is excluded via `.gitignore` and must stay that way.

## Project Overview

Diplomacy Conflict Solver and game server written in Python. Partial implementation of a Diplomacy game engine, focused
on the **conflict resolution algorithm** -- the most complex component of the game.

**Implemented:** Syntax service, Geography service (per Gilgamesch B.2.6 classification), Conflict resolution engine consuming `OrderGeoInfo`, Round orchestrator chaining all three, FastAPI routers per phase + `api_app.py` mount, Pydantic data models, DDL renderer for living diagrams, comprehensive test suite (DATC 10/10 + DipNet 96.4% PASS on 100-game sample).
**Partial:** Retreat-options enumeration (`geography/retreat.py`) — full retreat resolution still open.
**Not implemented:** Support-center counting, buildup / disband (winter adjustments).

## Game Round Pipeline

A complete Diplomacy round consists of these phases (see `project/doc/PHASES.md` for details):

```
Syntax → Geography → Conflict Resolution → Retreats → Support Centers → Buildup/Dissolve
```

| Phase                   | Status                          | Description                                                                                              |
| ----------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Syntax**              | **Implemented**                 | SYN-001..008. Strike invalid orders, inject hold-defaults for un-ordered units.                          |
| **Geography**           | **Implemented**                 | GEO-001..009 classifier per Gilgamesch B.2.6.1. Emits `OrderGeoInfo` + `ConvoyGraph`, no order rewrites. |
| **Conflict Resolution** | **Implemented**                 | Resolves conflicts using `OrderGeoInfo`. Honours B.4.2.9 / B.4.2.10 asymmetry. Superfields only.         |
| **Retreats**            | Partial (`retreat_options` only)| Candidate retreat enumeration; full conflict resolution between retreating units not yet implemented.    |
| **Support Centers**     | Not implemented                 | Count supply centers per nation.                                                                         |
| **Buildup/Dissolve**    | Not implemented                 | Build new units or disband excess.                                                                       |

The Conflict Resolver consumes `OrderGeoInfo` markers from Geography and optionally a `ConvoyGraph` for `eval_k1` convoy route validation. Subfield resolution (SpN/SpS → Spa) is handled by Geography.

**Notation convention for support/convoy:** The `dest` field of `msup` and `con` orders refers to the **starting field**
of the referenced unit (uniquely identifying it), not the target/destination of that unit's move. This works because
earlier phases guarantee the notation refers to a valid unit.

## Project Structure

```
project/
  dipworkpy/              # Core package
    __init__.py            # FastAPI app
    model.py               # Pydantic models (Order, Situation, ConflictResolution)
    conflict_game.py       # Main conflict resolution entry point
    graphs.py              # Pathfinding for convoy routing
    eval/              # 5-phase conflict resolution algorithm
      eval_k*.py           # Phase 0-4: uncontested, concoy, simple, border, chain.
      eval_k4.py           # Phase 4: chain/circular moves
      eval_model.py        # Internal models (t_field, t_order, t_world)
      eval_common.py       # Shared utilities
  tests/                   # Test suite
    test_conflict_game.py  # Core algorithm tests (7 scenarios)
    test_conflict_datc.py  # DATC compliance tests (10 cases)
    test_graphs.py         # Graph algorithm tests (13 cases)
    conftest.py            # Test fixtures and helpers
    TEST_CASES_DATC.md     # DATC test cases in DipworkPy notation
  tests_from_stpsyr/       # External DATC validation (98 test cases)
  test_data_pipeline/      # DipNet dataset test runner
    mappings.py            # DipNet→DipworkPy notation mapping
    dipnet_parser.py       # JSONL reader + DwpcrTestCase generator
    evaluator.py           # conflict_game runner + result comparison
    run_dipnet_tests.py    # CLI entry point + reporting
  NOTATION.md              # Notation guide (nations, territories, orders)
  pyproject.toml           # uv-managed project (PEP 621 + PEP 735 dependency-groups)
  Makefile                 # Build automation
  main.py                  # FastAPI entry point
```

## Key Technologies

- **Python 3.9+**, **Pydantic 2.x**, **FastAPI**, **Poetry**, **Pytest**, **Ruff + MyPy** (100% type clean)

## Notation System (DipworkPy Format)

Different from DATC standard -- uses fixed-length codes:

| Element     | DipworkPy                  | DATC Standard                   |
| ----------- | -------------------------- | ------------------------------- |
| Nations     | 2 letters: `Au`, `En`      | 3+ letters: `AUS`, `ENG`        |
| Territories | 3 letters: `Vie`, `NTH`    | Variable: `Vienna`, `North Sea` |
| Orders      | 3-4 letters: `mve`, `hsup` | Symbols: `-`, `S`               |
| Units       | 1 letter: `A`, `F`         | Same                            |

**Order format:** `<Nation> <Unit> <Current> <Order> <Destination>`

```
Au A Vie mve Mun    # Austria Army Vienna moves to Munich
En F Lon hsup ENG   # England Fleet London hold-supports English Channel
```

**Result markers:** `!` = failed, `>` = dislodged

```
Au A Vie mve Mun !  # Move failed (bounce)
En F Lon mve NTH >  # Unit dislodged
```

See `project/NOTATION.md` for the full reference.

## Development Commands

```bash
make check            # Full validation: core + DATC + STPSYR + lint (RECOMMENDED)
make verify           # Quick: core tests + demo
make install          # Install dependencies (Poetry)

make test-core        # Core conflict resolution (7 tests)
make test-datc        # DATC compliance (10 tests, 3 known failures)
make test-graphs      # Graph pathfinding (13 tests)
make test-stpsyr      # STPSYR external validation (3 simple scenarios)
make test-stpsyr-full # Full STPSYR parser (experimental, 33/98 working)

make test-dipnet-quick  # DipNet dataset (100 games, ~1600 test cases)
make test-dipnet-full   # DipNet dataset (all 33K games, ~500K tests, slow)

make lint             # ruff + mypy (currently 100% clean)
make format           # Code formatting
make dev              # Start FastAPI server on port 8000
```

## Algorithm: 5-Phase Conflict Resolution

Pipeline in `conflict_game.py`: parser -> k1 -> k2 -> k3 -> k4 -> k0 -> writer

1. **k1**: Convoy evaluation and route validation
2. **k2**: Support cutting and strength calculation
3. **k3**: Move conflict resolution
4. **k4**: Additional rule interpretations (IX.3, IX.7)
5. **k0**: Final support counting for uncontested areas

**Pattfields** (territories unavailable for retreats) are computed as:

```python
pattfields = (efields | ufields) - sfields - (hfields - efields)
```

**Configurable switches:**

- `self_cut_ok` - Can a nation cut its own support?
- `rule_interpretation_IX_3` - Dislodgement rules (0, 1, 2)
- `rule_interpretation_IX_7` - Additional conflict rules
- `convoy_routing_engine` - Convoy validation mode (`"always"` or `"fixed:..."`)

## Key Data Structures

**Input:** `Situation` containing `List[Order]` and optional `Switches`.
**Output:** `ConflictResolution` containing `List[OrderResult]` and `Set[str]` pattfields.

`OrderResult` extends `Order` with `succeeds: Optional[bool]` (None=success, False=failed) and
`dislodged: Optional[bool]`.

Internal models in `eval/eval_model.py`: `t_field` (unit with strengths and status), `t_world` (all fields +
switches).

## Testing Patterns

```python
# Test helpers from conftest.py:
mk_order("Au A Vie mve Mun")  # Full order
mk_order_h("Au A Vie hld")  # Hold (no destination)
mk_order_0("Au A Vie")  # No command (implicit hold)
mk_oresult("Au A Vie mve Mun !")  # Expected result with failure marker

# Test pattern:
situation = Situation(orders=[mk_order("Au A Vie mve Mun"), ...])
result = conflict_game(situation)
expected = ConflictResolution(orders=[mk_oresult("Au A Vie mve Mun"), ...])
assert result <= expected
```

All models have `__log__()` methods for debugging.

## Web API (FastAPI)

- `POST /dip_eval` - Main conflict resolution
- `POST /check` - Order validation (placeholder)
- `GET /` - Service status

## DATC Compliance

All 10 DATC test cases pass. Historical 6.D.2 / 6.D.3 / 6.F.1 failures resolved:
- **6.D.2** — was already passing at the start of the re-architecture session
- **6.D.3** / **6.F.1** — gated behind `Switches.pattfields_include_failed_dests` (default off), so the structurally-conflicting expectation in `test_conflict_game_02` also still passes

See `project/doc/DATC_ANALYSIS.md` for the per-case write-up.

## Future Priorities

1. Geography service with border validation and convoy pathfinding
2. Fix DATC compliance issues in k2/k3 phases
3. Retreat resolution
4. Winter adjustments (supply center counting, build/disband)

## Current Handoff State (2026-05-19)

Branch: `feat/service-architecture-and-ddl`.

Committed work in this branch:

- `82ae863 docs: document DWEX language conventions`
  - Adds `project/doc/DWEX-language.md`.
  - Adds a short DWEX intro to generated `project/doc/EXAMPLES.md`.
  - Uses canonical field name `ENG` instead of legacy `CHN` in examples/tests/demo.
- `c0b9281 feat: add explicit geography map schema`
  - Replaces the standard-map runtime schema with field-local `borders` and `neighbor_order`.
  - Adds explicit `$convoy` border marker; convoy semantics must not be inferred from `F` passability.
  - Adds `features`, `can_build`, `subfields`, `diversions`, and optional local FIELDS-source parity test.
  - Adds retreat option service/API using right-hand-rule ordering and always appending `ex`.
  - Adds split-coast tests for Spa/SpN/SpS, Bul/BuE/BuS, Pet/PeS and terrain invariants.

Uncommitted work currently present:

- Conflicter/round integration for `ConvoyGraph`:
  - `project/dipworkpy/conflict_game.py`
  - `project/dipworkpy/conflict/api.py`
  - `project/dipworkpy/round/orchestrator.py`
  - `project/dipworkpy/eval/eval_model.py`
  - `project/dipworkpy/eval/eval_k1.py`
  - `project/tests/test_conflict_convoy_graph.py`
- Purpose: k1 convoy route validation now uses the geography-produced `ConvoyGraph` when supplied, restricts it to surviving convoyers after k1 dislodgement, and falls back to legacy `convoy_routing_engine` only when no graph is supplied.
- There is also untracked IDE file `.idea/db-forest-config.xml`; leave it alone unless explicitly asked.

Fresh verification already run after the uncommitted integration:

```bash
cd project
make verify
uv run python -m pytest tests/test_conflict_convoy_graph.py tests/test_round_orchestrator.py tests/test_conflict_geo_info.py tests/test_geo_*.py tests/test_geography_*.py -q
uv run ruff check dipworkpy/eval/eval_model.py dipworkpy/eval/eval_k1.py dipworkpy/conflict_game.py dipworkpy/conflict/api.py dipworkpy/round/orchestrator.py tests/test_conflict_convoy_graph.py
uv run ruff format --check dipworkpy/eval/eval_model.py dipworkpy/eval/eval_k1.py dipworkpy/conflict_game.py dipworkpy/conflict/api.py dipworkpy/round/orchestrator.py tests/test_conflict_convoy_graph.py
uv run mypy dipworkpy/eval/eval_model.py dipworkpy/eval/eval_k1.py dipworkpy/conflict_game.py dipworkpy/conflict/api.py dipworkpy/round/orchestrator.py
```

Observed results:

- `make verify`: pass.
- Integration subset: `66 passed`.
- Earlier broad geography subset after schema merge: `99 passed, 1 skipped`.
- Ruff: pass.
- MyPy: pass for touched integration files.

Important implementation notes:

- Conflict resolver remains field-name agnostic and should receive normalized superfields.
- Convoy routing should work on superfields: armies start/end on superfields; sea fields have no subfields.
- Split-coast subfields are handled during early geography correction and retreat ordering, not inside the conflict algorithm.
- `standard.json` uses field-local `borders`; `MapDefinition`/`StandardMap` derive internal tuple-key `Edge`s for algorithmic use.
- `$convoy` is an explicit border marker and is independent of unit type `F`, so future variants can allow other convoying unit types.
- `tests/test_standard_map_fields_source.py` intentionally skips unless local `project/tests/standard.fields.txt` exists.

Suggested next tasks:

1. Commit the uncommitted Conflicter/ConvoyGraph integration as a small follow-up commit, e.g. `feat: route convoys through geography graph`.
2. Add an API-level test for `POST /conflict` with `convoy_graph` once the FastAPI/httpx test-client dependency issue is addressed.
3. Add/verify `POST /geography/retreat-options` API test if endpoint tests are runnable in the current environment.
4. Run a wider validation pass:
   - `make check` if feasible.
   - `make examples-check` after any DWEX changes.
   - Full geography/map/conflict subsets before committing.
5. Consider documenting the new standard-map JSON schema in `project/doc/GEOGRAPHY.md` or a dedicated schema doc if it grows further.
6. Keep the strict `./pas/` confidentiality rule: do not mention or include private source contents in docs, commits, or generated fixtures.
