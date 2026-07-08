# dipworkpy

## Strict Rules

- The `./pas/` directory is **private and confidential**. NEVER describe its contents, reference it in documentation,
  mention it in commits, or include it in git. It is excluded via `.gitignore` and must stay that way.

## Project Overview

Diplomacy Conflict Solver and game server written in Python. Partial implementation of a Diplomacy game engine, focused
on the **conflict resolution algorithm** -- the most complex component of the game.

**Implemented:** Syntax service, Geography service (per Gilgamesch B.2.6 classification), Conflict resolution engine consuming `OrderGeoInfo`, Round orchestrator chaining all three, FastAPI routers per phase + `api_app.py` mount, Pydantic data models, DDL renderer for living diagrams, comprehensive test suite (DATC = 10 hand-picked cases, DipNet = 96.4% on a 100-game sample; see `## DATC Compliance` for honest scope and `## Known Gaps` for the geography-not-yet-wired caveat).
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

## Current Plan, Handoff & Known Gaps

The living roadmap, DATC-compliance status (honest scope), current handoff state, suggested next tasks, known code gaps, and the adversarial plan review log now live in `AGENTS.md`. This file keeps the stable project reference only.
