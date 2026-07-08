# Internet-Test-Suites geography-aware + Conflict-Solver-Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Revision 5 — through 4 adversarial review rounds (confirmed critical/high: 22 → 5 → 1 → **0**, stop rule met in round 4); two rounds included instrumented dry runs of the wiring. See the review log at the bottom. **Cleared for execution.**

**Goal:** Make the two internet-sourced test suites (DipNet dataset runner in `project/test_data_pipeline/`, stpsyr DATC runner in `project/tests_from_stpsyr/`) feed geography output (`ConvoyGraph`, `OrderGeoInfo`) into the conflict resolver so convoy cases are actually adjudicated and verified — then fix the conflict-solver bugs those suites surface.

**Architecture:** The wiring already exists: `geography_phase(GeographyRequest(orders))` produces normalized orders + `OrderGeoInfo` + `ConvoyGraph`; `conflict_game(situation, order_geo_info=…, convoy_graph=…)` consumes them; `round_full()` in `project/dipworkpy/round/orchestrator.py` is the reference chain (syntax → geography → conflict). Both internet runners currently call bare `conflict_game(situation)`. This plan (a) fixes two engine-side defects that MUST land before wiring (GEO-004 validates msup against the wrong field; the evaluator's void→hld rewrite corrupts adjudication — root cause of both known DipNet FAILs), (b) wires the DipNet evaluator via `geography_phase` + `conflict_game`, (c) rewrites the stpsyr runner around `round_full` with a standard-1901 board and real result verification, (d) closes engine gaps (cmove dual source of truth, foreign-unit orders), and (e) triages + fixes the convoy failures that become visible.

**Tech Stack:** Python ≥3.9, Pydantic 2.x, pytest, uv (`uv run …` for everything), ruff + mypy.

## Baseline (measured 2026-07-07, HEAD `2bb3f47`, all verified by execution)

- **`make check` is RED today, twice over**: (1) `ruff check` fails with one `F401` (unused import `DwexUnit`) at `project/tests/test_dwex_model.py:2`; (2) behind it, **`ruff format --check` fails on 36 committed files** — currently masked because `lint-check-ruff` aborts `make lint` before `lint-check-format` runs. Task 0 fixes both. `uv run mypy dipworkpy/` has **4 pre-existing errors** (3 in `dipworkpy/graphs.py`, 1 in `dipworkpy/tools/dwex/cli.py`); the Makefile `lint` target tolerates mypy failures (prints a warning) — these 4 are NOT in scope, but no task may add new mypy errors.
- **`AGENTS.md` is untracked and `CLAUDE.md` carries uncommitted edits.** This plan cites AGENTS.md normatively (known gaps, roadmap) and Task 11 updates both — Task 0 commits their current state first so the execution worktree has them and Task-11 diffs stay clean.
- `uv run python -m pytest tests/ -q` (from `project/`): **239 passed, 1 skipped, 1 xfailed** — the full pytest suite is green.
- `make test-dipnet-quick` (100 games, 1602 cases): **1545 PASS (96.4%), 2 FAIL, 0 ERROR, 55 INCONCLUSIVE (all "convoy")**. The make target **exits nonzero by design** whenever FAIL > 0 — every gate below compares the printed counts, not the exit code.
- The 2 DipNet FAILs (`1IbGdARWCes1lsqm_F1906M`, `_xh_i5Do4jzgx8yS_F1906M`) are **NOT engine bugs**: feeding the original orders directly into `conflict_game` adjudicates both correctly (verified). The failures are caused by the evaluator's void→hld rewrite (`evaluator.py:138-148`): DipNet marks e.g. `A KIE S A BER - MUN` as `void` when the support targets an attack on the own nation's unit (support counts for bouncing third parties, never for dislodgement — DATC 6.D family); rewriting those supports to holds deletes their bounce strength and flips neighbouring adjudications. Task 3 removes the rewrite.
- **Geography has a support-validation bug (GEO-004)**: `geography/service.py:86-90` passes `supported_target=o.dest` (the supported unit's START field, per DipworkPy msup notation) to `classify_support`, which checks the supporter can reach that field. For **msup** the rule is: the supporter must reach the supported move's **DESTINATION**. Wiring geography before fixing this mass-invalidates legitimate supports and collapses the DipNet benchmark (measured by review: PASS drops to ≈46%). Task 2 fixes it BEFORE any wiring.
- `make test-stpsyr-full`: **silent no-op** (cwd-relative paths; finds 0 files, exits 0). Run from the correct directory: 33/88 parsed cases "execute" (= don't crash; **no result verification exists**, TODO at `stpsyr_test_runner.py:262-264`), 55 crash on `LookupError: fieldname X twice in current` (multi-phase cases flattened). On-disk reality: **93 `# N.` headers, 92 parseable cases** (a=12, b=12, c=7, d=33, e=15, f=13; `6.b` case 14 is a header-only `// TODO (pending builds)` stub). 4 cases are currently lost to `//`-comment lines corrupting the parser state machine (the 5th missing case is that stub).

## Global Constraints

- Python ≥3.9 (`requires-python = ">=3.9"`, mypy `python_version = "3.9"`): no `match`, no `X | None` annotations in runtime code (use `Optional[X]`), no 3.10+ stdlib.
- Run everything through uv: `uv run python -m pytest …`. Never bare `python`. All make targets and pytest runs happen from `project/` (`make -C project <target>` / `cd project`).
- **Standard gate** (run after EVERY task, all four commands, from `project/`):
  1. `make check` → green (from Task 0 onward),
  2. `uv run python -m pytest tests/ -q` → ≥239 passed, 0 failed,
  3. `uv run python -m pytest test_data_pipeline/tests/ -q` → green (exists from Task 3 onward),
  4. `uv run python -m pytest tests_from_stpsyr/test_stpsyr_parser.py -q` → green (exists from Task 6 onward).
  Plus the task-specific suite runs named in each task. `make test-dipnet-quick` exits nonzero while any FAIL remains — always evaluate its printed counts, never its exit code.
- ruff config includes `E4,E7,E9,F,W` with **E743**: helper functions must not be named `O`/`I`/`l` — this plan uses `mko`/`mkr`. Snippets in this plan are content-correct but not guaranteed format-canonical: run `uv run ruff format <changed files>` before EVERY commit (Task 0 makes the whole tree format-clean first, so formatting stays scoped to your own edits afterwards).
- Line numbers cited for `dipworkpy/geography/*`, `dipworkpy/syntax/*` and other reformatted files are **pre-reformat** (Task 0 reformats 36 files) — locate edit sites by the quoted anchor code, not by line number.
- mypy: no new errors. The 4 pre-existing errors (3 in `dipworkpy/graphs.py`, 1 in `dipworkpy/tools/dwex/cli.py`) stay untouched.
- The Strict Rules in the project `CLAUDE.md` apply, in particular the confidentiality rule about the private directory named there: never reference it in code, tests, docs, fixtures, or commits.
- **Git hygiene:** the working tree carries unrelated noise (`.pi/`, `.idea/`, modified `CLAUDE.md`/`.gitignore`, untracked `AGENTS.md`, `progress.md`). NEVER `git add -A`, `git add .`, or `git commit -a`. Every commit stages exactly the files listed in its step.
- Commit after every task, conventional-commit style matching the repo (`feat:`, `fix:`, `test:`, scope optional). Commit body explains **why**, not what.
- DipworkPy notation: nations 2 letters (`Au`, `En`), territories 3 letters (`Vie`, `NTH`), orders `mve/hld/msup/hsup/con`. **`msup`/`con` `dest` = STARTING field of the referenced unit**, not its target. Result markers: `!` = failed (`succeeds=False`), `>` = dislodged (`dislodged=True`). `succeeds=None` means SUCCESS — never truth-test `succeeds` directly.
- The conflict resolver works on **superfields only** (`Spa`, not `SpN`/`SpS`). This plan keeps BOTH internet suites superfield-only end-to-end (coast fidelity is a documented, out-of-scope limitation — see Task 10 bucket B).
- `OrderGeoInfo.order_index` is positional: always pass **`geo.orders`** (geography's output list) as `Situation.orders` to `conflict_game` — never the pre-geography list, never filtered/reordered.
- Test helpers `mk_order(...)` / `mk_oresult(...)` are module-level functions in `project/tests/test_conflict_game.py` (NOT in conftest.py). New engine tests define their own small helpers (`mko`/`mkr`) rather than importing across test modules.

## File Structure (created/modified)

| File | Responsibility |
| --- | --- |
| `project/tests/test_dwex_model.py` | MODIFY (Task 0): remove unused import |
| 36 files in `project/dipworkpy/`+`project/tests/` | MODIFY (Task 0): mechanical ruff format |
| `AGENTS.md`, `CLAUDE.md` | ADD/COMMIT current state (Task 0); status refresh (Task 11) |
| `project/tests_from_stpsyr/stpsyr_test_runner.py` | MODIFY (Task 1), REWRITE (Tasks 6+7) |
| `project/dipworkpy/geography/service.py`, `project/dipworkpy/geography/rules.py` | MODIFY (Task 2): GEO-004 msup target |
| `project/tests/test_geography_msup_target.py` | CREATE (Task 2) |
| `project/test_data_pipeline/evaluator.py` | MODIFY (Task 3): wire geography, drop void rewrite, drop convoy exemption |
| `project/test_data_pipeline/tests/__init__.py`, `.../test_evaluator_geography.py` | CREATE (Task 3) |
| `project/dipworkpy/conflict_game.py` | MODIFY (Task 4): cmove promotion from `cmove_candidates` |
| `project/tests/test_conflict_game_convoy_source.py` | CREATE (Task 4) |
| `project/dipworkpy/syntax/rules.py`, `project/dipworkpy/syntax/service.py` | MODIFY (Task 5): SYN-009 |
| `project/tests/test_syntax_syn009.py` | CREATE (Task 5) |
| `project/tests_from_stpsyr/test_stpsyr_parser.py` | CREATE (Task 6) |
| `project/test_data_pipeline/tests/fixtures/*.json` + `.../test_dipnet_regressions.py` | CREATE (Task 8) |
| `project/tests/test_conflict_chain_characterization.py` | CREATE (Task 8) |
| `project/doc/DIPNET_CONVOY_TRIAGE.md`, `project/doc/STPSYR_TRIAGE.md` | CREATE (Tasks 9, 10) |
| `CLAUDE.md`, `AGENTS.md`, memory | MODIFY (Task 11): status refresh |

Task order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11. Tasks 4 and 8 are independent of the stpsyr lane (6, 7) and may be reordered against it; Task 5 must land BEFORE Task 7 (SYN-009 is consumed by the runner's verification and baseline); Task 3 hard-depends on Task 2; Task 7 hard-depends on Tasks 5 and 6; Tasks 9/10 come after everything upstream of their suite.

---

### Task 0: Baseline grün machen (ruff F401 + Format-Drift + Doku tracken)

**Files:**
- Modify: `project/tests/test_dwex_model.py:1-3`
- Modify: 36 files under `project/dipworkpy/` and `project/tests/` (mechanical `ruff format`)
- Add to git: `AGENTS.md`, current `CLAUDE.md` state

**Interfaces:**
- Produces: `make check` green — the precondition for every later gate; AGENTS.md/CLAUDE.md tracked so the execution worktree carries the plan's reference docs.

- [ ] **Step 1: Reproduce BOTH red causes**

Run: `make -C project check` → fails at `lint-check-ruff` with `F401 … DwexUnit imported but unused — tests/test_dwex_model.py:2`.
Run: `cd project && uv run ruff format --check dipworkpy/ tests/` → `36 files would be reformatted` (masked behind the F401 in the make chain — `lint: lint-check-ruff lint-check-format` stops at the first failure).

- [ ] **Step 2: Fix the F401, commit 1**

In `project/tests/test_dwex_model.py` remove `DwexUnit` from the import list (line 2).

```bash
git add project/tests/test_dwex_model.py
git commit -m "chore: unbreak ruff check (unused DwexUnit import)

Baseline for the internet-test-suite plan: every task gates on
'make check green'."
```

- [ ] **Step 3: Mechanical reformat, commit 2**

```bash
cd project && uv run ruff format dipworkpy/ tests/
uv run python -m pytest tests/ -q   # must still be 239 passed
cd .. && git add project/dipworkpy project/tests
git commit -m "style: ruff-format baseline (36 files)

lint-check-format was red but masked behind the ruff F401 (make lint
stops at the first failing prerequisite). Mechanical ruff format, no
behavior change — required so the per-task 'make check green' gate can
exist at all."
```

(`git add` of the two source trees is safe here: `git status --short project/` is empty at baseline, so exactly the reformatted files are staged. Verify that before staging.)

- [ ] **Step 4: Track the reference docs, commit 3**

The plan cites `AGENTS.md` normatively (known gaps, roadmap, review log) and Task 11 updates it and `CLAUDE.md` — but AGENTS.md is untracked and CLAUDE.md carries uncommitted edits. **Execution-order constraint:** untracked/modified files do not travel into a fresh worktree — this step MUST run in the main working copy BEFORE any execution worktree is created (or execute the whole plan in the main checkout). Commit their CURRENT state unchanged:

```bash
git add AGENTS.md CLAUDE.md docs/superpowers/plans/2026-07-07-internet-tests-geography-conflict-fixes.md
git commit -m "docs: track living plan/handoff docs (AGENTS.md)

The implementation plan references AGENTS.md normatively; execution in
a fresh worktree needs it, and committing the current state keeps the
final status-refresh diff reviewable."
```

(`progress.md` stays untracked — stale scratch, not referenced by this plan. Do NOT stage `.pi/`, `.idea/`, `.gitignore`.)

- [ ] **Step 5: Verify**

Run: `make -C project check` → green end-to-end (the mypy warning about pre-existing errors is tolerated by the Makefile — expected output, not a failure).
Run: `cd project && uv run python -m pytest tests/ -q` → 239 passed, 1 skipped, 1 xfailed.

---

### Task 1: stpsyr runner — cwd-unabhängige Pfade + ehrlicher Exit-Code

**Files:**
- Modify: `project/tests_from_stpsyr/stpsyr_test_runner.py` (lines 14, 293-322)

**Interfaces:**
- Produces: `make -C project test-stpsyr-full` finds and runs the 6 `datc-6.*.txt` files regardless of cwd; exits 1 when 0 test files were found.

- [ ] **Step 1: Reproduce the no-op**

Run: `make -C project test-stpsyr-full`
Expected: 6× `⚠️  Test file datc-6.X.txt not found`, `Total tests executed: 0/0`, exit 0. This is the bug.

- [ ] **Step 2: Fix path resolution and exit semantics**

In `project/tests_from_stpsyr/stpsyr_test_runner.py` replace line 14:

```python
sys.path.insert(0, '..')  # Add parent directory to path
```

with:

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))  # project/ on sys.path
```

In `main()` replace the loop body (lines 306-312):

```python
    for filename in test_files:
        if os.path.exists(filename):
            passed, tests = runner.run_file(filename, verbose=True)
```

with:

```python
    for filename in test_files:
        path = os.path.join(BASE_DIR, filename)
        if os.path.exists(path):
            passed, tests = runner.run_file(path, verbose=True)
```

(keep the `else: print(...)` branch), and directly after the loop add:

```python
    if total_tests == 0:
        print("❌ No test files found — path bug?")
        return 1
```

- [ ] **Step 3: Verify**

Run: `make -C project test-stpsyr-full`
Expected: `Found N test cases` per file, `Total tests executed: 33/88` (±0), exit 1 (55 cases still crash — that is Task 6/7 scope; this target is not part of `make check`).
Standard gate (Global Constraints) → green.

- [ ] **Step 4: Commit**

```bash
git add project/tests_from_stpsyr/stpsyr_test_runner.py
git commit -m "fix(stpsyr): resolve test files relative to the script, not cwd

make test-stpsyr-full ran from project/ and silently found zero test
files while reporting success — the suite has been a no-op in CI-style
usage. Zero discovered files is now a hard failure."
```

---

### Task 2: GEO-004 — msup validiert gegen das Move-ZIEL, nicht das Startfeld

**Files:**
- Modify: `project/dipworkpy/geography/service.py` (msup branch, lines 86-90 pre-reformat — locate by anchor code)
- Modify: `project/dipworkpy/geography/rules.py` (`classify_support`, line 183 pre-reformat) — signature gains the move-destination
- Create: `project/tests/test_geography_msup_target.py`

**Documented decision (do not "fix" without data):** a msup whose companion move is itself geo-INVALID still validates by reach-check only (the engine's B.4.2.9 downgrade of the invalid move governs the outcome). Whether such supports should instead be GEO-004-void (stricter DATC reading) is an open question parked on the Task 9/10 triage watchlists — decide there from measured cases, not here.

**Interfaces:**
- Consumes: `army_dest_by_start: Dict[str, str]` — already built in `geography_phase` (service.py:50-54) from companion `mve` orders (superfield-normalized). Note: despite the name it indexes ALL movers (armies and fleets).
- Produces: `classify_support(o, m, supported_target=…, move_dest=…, order_index=…)` where `move_dest` is `None` for hsup and the supported unit's move destination for msup. GEO-004 semantics: **hsup** → supporter must reach the held unit's field (unchanged); **msup** → supporter must reach the supported move's destination; **msup whose referenced unit has no mve order** → invalid (GEO-004, support-to-move without a move), `holds_supportable`.

**Why (verified):** `service.py:86-90` passes `supported_target=o.dest` — the supported unit's START field — for both hsup and msup, and `classify_support` checks reachability of that field. Correct Diplomacy rule for support-to-move: the supporter must be able to reach the **destination** of the supported move. Consequences today: `Ge A Mun msup War` (supporting `Ru A War mve Sil`; Mun↔Sil adjacent, Mun↔War NOT adjacent) is falsely invalidated; `Ge A Mun msup Sil` (supporting `Ru A Sil mve War`; Mun↔War not adjacent) is falsely validated. Wiring geography without this fix collapses the DipNet pass rate to ≈46% (measured in review).

- [ ] **Step 1: Write the failing tests**

Create `project/tests/test_geography_msup_target.py`:

```python
"""GEO-004: support-to-move must validate against the move's destination."""

from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current,
                 order=order, dest=dest)


def _geo_for(orders, current):
    geo = geography_phase(GeographyRequest(orders=orders))
    idx = next(i for i, o in enumerate(geo.orders) if o.current == current)
    return geo.order_geo_info[idx]


def test_msup_valid_when_supporter_reaches_move_dest():
    # Mun<->Sil adjacent, Mun<->War NOT adjacent: support is legal.
    orders = [
        mko("Ru", "A", "War", OrderType.mve, "Sil"),
        mko("Ge", "A", "Mun", OrderType.msup, "War"),
    ]
    info = _geo_for(orders, "Mun")
    assert info.is_valid, info


def test_msup_invalid_when_supporter_cannot_reach_move_dest():
    # Supported move goes to War; Mun cannot reach War.
    orders = [
        mko("Ru", "A", "Sil", OrderType.mve, "War"),
        mko("Ge", "A", "Mun", OrderType.msup, "Sil"),
    ]
    info = _geo_for(orders, "Mun")
    assert not info.is_valid, info
    assert info.invalidity_code == "GEO-004", info
    assert info.effective_behavior == "holds_supportable", info


def test_msup_without_companion_move_is_invalid():
    # Referenced unit holds -> support-to-move is void.
    orders = [
        mko("Ru", "A", "Sil", OrderType.hld),
        mko("Ge", "A", "Mun", OrderType.msup, "Sil"),
    ]
    info = _geo_for(orders, "Mun")
    assert not info.is_valid, info
    assert info.invalidity_code == "GEO-004", info


def test_hsup_unchanged_checks_held_units_field():
    orders = [
        mko("En", "F", "Lon", OrderType.hld),
        mko("En", "F", "NTH", OrderType.hsup, "Lon"),
    ]
    info = _geo_for(orders, "NTH")
    assert info.is_valid, info
```

- [ ] **Step 2: Run to verify red**

Run: `cd project && uv run python -m pytest tests/test_geography_msup_target.py -v`
Expected: `test_msup_valid_when_supporter_reaches_move_dest` FAILs (falsely invalid), `test_msup_invalid_when_supporter_cannot_reach_move_dest` FAILs (falsely valid), `test_msup_without_companion_move_is_invalid` FAILs (currently valid — Mun↔Sil adjacent), `test_hsup_unchanged_checks_held_units_field` PASSes.

- [ ] **Step 3: Implement**

In `project/dipworkpy/geography/rules.py`, extend `classify_support`:

```python
def classify_support(
    o: Order,
    m: MapProtocol,
    *,
    supported_target: str,
    order_index: int,
    move_dest: Optional[str] = None,
    is_msup: bool = False,
) -> OrderGeoInfo:
    """GEO-004. hsup: supporter must reach the held unit's field.
    msup: supporter must reach the supported MOVE's destination
    (move_dest); a msup whose referenced unit has no mve order is void.

    Per Gilgamesch B.3.1.1: no convoy, no furt — strict direct adjacency.
    """
    if not m.field_exists(supported_target):
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=f"supported target {supported_target!r} unknown",
            effective_behavior="holds_supportable",
        )
    if is_msup and move_dest is None:
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=(
                f"support-to-move for {supported_target!r}, "
                f"but that unit has no move order"),
            effective_behavior="holds_supportable",
        )
    reach_target = move_dest if is_msup else supported_target
    if not can_reach_by_unit(o.current, reach_target, o.utype, m):
        return OrderGeoInfo(
            order_index=order_index,
            is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=(f"{o.utype} {o.current} cannot reach {reach_target} directly"),
            effective_behavior="holds_supportable",
        )
    return OrderGeoInfo(
        order_index=order_index,
        is_valid=True,
        effective_behavior="moves",
    )
```

(`Optional` is already imported in rules.py or add `from typing import Optional`.)

In `project/dipworkpy/geography/service.py` replace the support branch (lines 85-90):

```python
        elif o.order in (OrderType.hsup, OrderType.msup):
            # supported_target = o.dest (location of supported unit per
            # DipworkPy notation)
            target = o.dest if o.dest else o.current
            info = classify_support(o, m, supported_target=target, order_index=i)
```

with:

```python
        elif o.order in (OrderType.hsup, OrderType.msup):
            # supported_target = o.dest (location of supported unit per
            # DipworkPy notation). For msup, GEO-004 must check the
            # supported MOVE's destination, looked up via the companion
            # mve order (army_dest_by_start indexes all movers).
            target_raw = o.dest if o.dest else o.current
            target = normalize_to_superfield(target_raw, m)
            info = classify_support(
                o, m,
                supported_target=target,
                order_index=i,
                move_dest=army_dest_by_start.get(target),
                is_msup=(o.order == OrderType.msup),
            )
```

- [ ] **Step 4: Verify**

Run: `cd project && uv run python -m pytest tests/test_geography_msup_target.py -v` → 4 PASS.
Standard gate → green — with ONE known deterministic casualty: `tests/test_round_orchestrator.py::test_full_round_b429_invalid_mve_not_hold_supportable` WILL fail, because its auxiliary support `Ge A Sil msup Boh` (supporting Boh→Vie) encodes the OLD semantics — Sil cannot reach the move destination Vie, so the support is now correctly GEO-004-void and Vie is no longer dislodged. Repair the TEST, not the code: replace the supporter with a Vie-adjacent unit, e.g. `Ge A Gal msup Boh` (Gal→Vie adjacency holds), restoring attack strength 2 and the test's B.4.2.9 intent; say so in the commit body and stage the test file. Any OTHER failing test: stop and re-check the implementation before assuming it encodes the bug.

- [ ] **Step 5: Commit**

```bash
git add project/dipworkpy/geography/rules.py project/dipworkpy/geography/service.py project/tests/test_geography_msup_target.py
git commit -m "fix(geography): GEO-004 validates msup against the move destination

classify_support checked reachability of the supported unit's START
field for support-to-move orders. The Diplomacy rule requires the
supporter to reach the move's DESTINATION. With the old check, wiring
geography into the DipNet evaluator mass-invalidated legitimate
supports (pass rate collapse 96%->46% in review measurement). msup
referencing a non-moving unit is now void per the same rule."
```

---

### Task 3: DipNet-Evaluator — Geography wiren, Void-Rewrite streichen, Convoys werten

**Files:**
- Modify: `project/test_data_pipeline/evaluator.py` (imports; void block lines 127-148; engine call lines 150-156; convoy exemption lines 178-187; docstring)
- Create: `project/test_data_pipeline/tests/__init__.py` (empty), `project/test_data_pipeline/tests/test_evaluator_geography.py`

**Interfaces:**
- Consumes: Task 2's GEO-004 fix (hard prerequisite), `geography_phase` / `GeographyRequest`.
- Produces: `evaluate_test_case(tc)` runs geography+conflict on the ORIGINAL orders (no void rewrite; void orders still excluded from comparison via `void_keys`), and convoy cases score PASS/FAIL (never `INCONCLUSIVE(reason="convoy")`).

**Design decisions (fixed, from verified root-cause analysis + review round 2's measured dry run):**
1. **Replace the blanket void→hld rewrite with a SELECTIVE one.** DipNet `void` covers (at least) two classes:
   - *Own-unit-attack supports* (statement matches the referenced unit's actual order): they still bounce third parties in the dataset's adjudication. Rewriting them to holds deletes that strength — this caused both known DipNet FAILs (verified: the engine adjudicates the original orders correctly). These must pass through LIVE.
   - *Mismatch supports* (statement contradicts the referenced unit's actual order): a hold-support on a unit that actually MOVES, or a move-support whose stated destination differs from the actual move. DipworkPy notation cannot even represent the mismatch (`msup dest` = unit start; the engine re-points to the ACTUAL move), so passed through live they wrongly count — measured: 24 PASS→FAIL regressions in the round-2 dry run (e.g. `-joCH1jONGKS0wBT_F1903M`: `A MUN S A TYR` void because TYR moves; live hsup wrongly protects Tyr). These get rewritten to `hld`.
   Mismatch is detectable at parse time from the raw DipNet strings; rewrite exactly `void ∩ mismatch`. The `void_keys` comparison skip stays for ALL void orders.
2. **Failed-move comparison mapping.** The engine reports a geo-invalid move as `hld` with `succeeds=None` (B.4.2.9 demotion); DipNet expects the move with `succeeds=False`. Measured: 7 PASS→FAIL regressions. `_compare_orders` treats `expected.order==mve` vs `actual.order==hld` (same unit) as a FAILED move: the unit stayed put either way.
3. Drop `Switches(convoy_routing_engine="always")` — dead once `convoy_graph` is passed.
4. Delete the `has_convoy → INCONCLUSIVE` branch outright. `ResultSummary.inconclusive_convoy` field stays for output-format compat (reads 0).
5. Expected end state — **measured by the round-3 review emulation of this exact design**: **1561 PASS / 41 FAIL / 0 ERROR / 0 INCONCLUSIVE**; 38 of the FAILs are convoy-related, 3 are the live own-unit-attack void-support family in bounce chains (`h9QEPT6s5-Fi1WrV_F1910M`, `kLq1Qi6MqjKKDd4G_F1917M`, `5M65XaqXlieNDQVV_S1907M`) — all 41 are Task 9's triage work list, none block Task 3.

- [ ] **Step 1: Write the tests**

Create `project/test_data_pipeline/tests/__init__.py` (empty) and `project/test_data_pipeline/tests/test_evaluator_geography.py`:

```python
"""Regression tests: evaluator adjudicates convoys via geography and
feeds ORIGINAL orders to the engine (no void rewrite)."""

from dipworkpy.model import Order, OrderResult, OrderType

from test_data_pipeline.dipnet_parser import DwpcrTestCase
from test_data_pipeline.evaluator import TestResult, evaluate_test_case


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current,
                 order=order, dest=dest)


def mkr(nation, utype, current, order, dest=None, succeeds=None, dislodged=None):
    return OrderResult(nation=nation, utype=utype, current=current,
                       order=order, dest=dest,
                       succeeds=succeeds, dislodged=dislodged)


def _case(case_id, orders, expected, has_convoy, void_indices=(),
          mismatch_indices=()):
    return DwpcrTestCase(
        id=case_id, orders=orders, expected=expected,
        has_convoy=has_convoy, has_void=bool(void_indices),
        source_phase="TEST", source_game="TEST",
        void_order_indices=list(void_indices),
        mismatch_support_indices=list(mismatch_indices),
    )


def test_broken_convoy_route_fails_the_move():
    """F ADR cannot convoy Lon->Nor. The legacy 'always' engine let any
    surviving convoyer validate the route; with geography the move must
    not succeed. Asserting PASS (not merely != INCONCLUSIVE, which
    becomes vacuous once the branch is deleted): the expected results
    encode the failed move, so PASS means the engine agrees."""
    tc = _case(
        "synthetic_convoy_broken",
        orders=[
            mko("En", "A", "Lon", OrderType.mve, "Nor"),
            mko("En", "F", "ADR", OrderType.con, "Lon"),
        ],
        expected=[
            mkr("En", "A", "Lon", OrderType.mve, "Nor", succeeds=False),
            mkr("En", "F", "ADR", OrderType.con, "Lon"),
        ],
        has_convoy=True,
    )
    result = evaluate_test_case(tc, keep_details=True)
    assert result.result == TestResult.PASS, (result.reason, result.diffs)


def test_valid_convoy_is_adjudicated_pass():
    """Characterization (passes before AND after): clean convoy PASSes."""
    tc = _case(
        "synthetic_convoy_ok",
        orders=[
            mko("En", "A", "Lon", OrderType.mve, "Nor"),
            mko("En", "F", "NTH", OrderType.con, "Lon"),
        ],
        expected=[
            mkr("En", "A", "Lon", OrderType.mve, "Nor"),
            mkr("En", "F", "NTH", OrderType.con, "Lon"),
        ],
        has_convoy=True,
    )
    result = evaluate_test_case(tc)
    assert result.result == TestResult.PASS, result


def test_void_support_still_bounces_third_party():
    """DipNet-void support (attack on own unit) keeps its bounce strength.

    Fr Ber->Mun (Kie+Ruh support, both dataset-void because Mun is
    French) vs Au Tyr->Mun (Boh support) while Fr Mun->Sil bounces:
    nothing may enter Mun and Mun must not be dislodged. With the old
    void->hld rewrite Tyr won Mun — that was DipNet FAIL _xh_i5Do.
    """
    orders = [
        mko("Au", "A", "Tyr", OrderType.mve, "Mun"),
        mko("Au", "A", "Boh", OrderType.msup, "Tyr"),
        mko("Fr", "A", "Ber", OrderType.mve, "Mun"),
        mko("Fr", "A", "Mun", OrderType.mve, "Sil"),
        mko("Fr", "A", "Kie", OrderType.msup, "Ber"),
        mko("Fr", "A", "Ruh", OrderType.msup, "Ber"),
        mko("Au", "A", "Sil", OrderType.hld),
    ]
    expected = [
        mkr("Au", "A", "Tyr", OrderType.mve, "Mun", succeeds=False),
        mkr("Au", "A", "Boh", OrderType.msup, "Tyr"),
        mkr("Fr", "A", "Ber", OrderType.mve, "Mun", succeeds=False),
        mkr("Fr", "A", "Mun", OrderType.mve, "Sil", succeeds=False),
        # Kie/Ruh are void-marked in the dataset: excluded via void_keys,
        # their expected entries are irrelevant but must exist.
        mkr("Fr", "A", "Kie", OrderType.msup, "Ber"),
        mkr("Fr", "A", "Ruh", OrderType.msup, "Ber"),
        mkr("Au", "A", "Sil", OrderType.hld),
    ]
    tc = _case("synthetic_void_support", orders, expected,
               has_convoy=False, void_indices=(4, 5))
    result = evaluate_test_case(tc)
    assert result.result == TestResult.PASS, result


def test_mismatch_hold_support_is_rewritten_not_live():
    """A hold-support on a unit that actually MOVES is dataset-void AND
    a statement mismatch -> rewritten to hld, so it must NOT protect
    the mover from dislodgement (round-2 regression class, 24 cases,
    e.g. -joCH1jONGKS0wBT_F1903M)."""
    orders = [
        mko("Au", "A", "Tyr", OrderType.mve, "Tri"),   # bounces on Tri
        mko("Ru", "A", "Tri", OrderType.hld),
        mko("It", "A", "Ven", OrderType.mve, "Tyr"),
        mko("It", "A", "Pie", OrderType.msup, "Ven"),
        mko("Ge", "A", "Mun", OrderType.hsup, "Tyr"),  # void+mismatch: Tyr moves
    ]
    expected = [
        mkr("Au", "A", "Tyr", OrderType.mve, "Tri", succeeds=False, dislodged=True),
        mkr("Ru", "A", "Tri", OrderType.hld),
        mkr("It", "A", "Ven", OrderType.mve, "Tyr"),
        mkr("It", "A", "Pie", OrderType.msup, "Ven"),
        mkr("Ge", "A", "Mun", OrderType.hsup, "Tyr"),  # void -> comparison-skipped
    ]
    tc = _case("synthetic_mismatch_support", orders, expected,
               has_convoy=False, void_indices=(4,), mismatch_indices=(4,))
    result = evaluate_test_case(tc, keep_details=True)
    assert result.result == TestResult.PASS, (result.reason, result.diffs)


def test_geo_invalid_move_compares_as_failed_move():
    """Engine demotes an illegal move to hld/succeeds=None (B.4.2.9);
    DipNet expects mve/succeeds=False. The comparison maps the two
    (round-2 regression class, 7 cases)."""
    tc = _case(
        "synthetic_invalid_move",
        orders=[mko("Tu", "A", "Con", OrderType.mve, "Seb")],
        expected=[mkr("Tu", "A", "Con", OrderType.mve, "Seb", succeeds=False)],
        has_convoy=False,
    )
    result = evaluate_test_case(tc, keep_details=True)
    assert result.result == TestResult.PASS, (result.reason, result.diffs)
```

- [ ] **Step 2: Run to verify red/green split**

Run: `cd project && uv run python -m pytest test_data_pipeline/tests/ -v`
Expected: red across the board today — the module fails at collection/`_case` because `DwpcrTestCase` has no `mismatch_support_indices` field yet. After adding the field (Step 3a) but before the evaluator changes: `test_valid_convoy_is_adjudicated_pass` AND `test_mismatch_hold_support_is_rewritten_not_live` PASS (the old BLANKET rewrite also rewrites the mismatch support — that test guards the selective rewrite from the other side: it goes red if someone drops the rewrite entirely); the decisive reds are `test_void_support_still_bounces_third_party` (blanket rewrite deletes live supports), `test_broken_convoy_route_fails_the_move` (INCONCLUSIVE today), and `test_geo_invalid_move_compares_as_failed_move`. If a marker detail diffs for an unexpected reason, verify the engine's actual adjudication by hand (run the orders through `round_full` in a scratch script) before adjusting `expected`.

- [ ] **Step 3: Implement**

a) In `project/test_data_pipeline/dipnet_parser.py`: add the field to `DwpcrTestCase`:

```python
    # Indices of support orders whose raw DipNet statement contradicts
    # the referenced unit's actual order (hold-support on a mover;
    # move-support with a different stated destination). Only the
    # intersection with void_order_indices gets rewritten to hld.
    mismatch_support_indices: List[int] = field(default_factory=list)
```

and compute it in `parse_movement_phase` from the RAW order strings (before translation). Helper:

```python
def _support_mismatch(order_str: str, orders_by_loc: dict) -> bool:
    """True when a support statement contradicts the referenced unit's
    actual order. order_str like 'A MUN S A VIE - BUD' / 'A MUN S A VIE'."""
    parts = order_str.split()
    if len(parts) < 5 or parts[2] != "S":
        return False
    ref_loc = convert_territory(parts[4])
    actual = orders_by_loc.get(ref_loc)
    if actual is None:
        return True                       # support of a non-existent order
    aparts = actual.split()
    actual_is_move = len(aparts) >= 4 and aparts[2] == "-"
    if len(parts) >= 7 and parts[5] == "-":      # stated support-to-move
        if not actual_is_move:
            return True
        return convert_territory(parts[6]) != convert_territory(aparts[3])
    return actual_is_move                 # stated support-to-hold on a mover
```

with `orders_by_loc` built once per phase as a plain loop over ALL raw order strings (key: `convert_territory(parts[1])`, value: the raw string). Indexing convention: `mismatch_support_indices` holds positions in `tc.orders`, i.e. the SAME enumeration order in which `parse_movement_phase` appends parsed orders — compute the mismatch flag in that same loop so the indices can't drift. Guard `convert_territory` `KeyError`s AND short-token `IndexError`s on malformed raw strings: treat as not-mismatch and append a `parse_warnings` entry instead of raising. Compute the mismatch flag immediately after `parse_dipnet_order` succeeds and append `len(dwp_orders) - 1` — mirroring how `void_order_indices` is built, so indices index the SURVIVING orders list.

b) In `project/test_data_pipeline/evaluator.py` add imports:

```python
from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
```

c) Replace the blanket void-rewrite block (lines 136-148) with the selective one below, AND delete the now-unused `void_indices_set = set(tc.void_order_indices)` assignment at line 129 (ruff F841 bites at the gate otherwise). The `void_keys` construction loop (lines 127-133 minus that assignment) stays:

```python
    # Selective rewrite: only void supports whose STATEMENT contradicts
    # the referenced unit's actual order become holds (they are
    # unrepresentable in DipworkPy msup notation and must not count).
    # All other void orders — e.g. supports of an attack on an own unit,
    # which still bounce third parties — stay live; geography/B.4.2.x
    # handles genuinely invalid orders. void_keys still excludes every
    # void order from result comparison.
    rewrite = set(tc.void_order_indices) & set(tc.mismatch_support_indices)
    if rewrite:
        engine_orders = [
            o.model_copy(update={"order": OrderType.hld, "dest": None})
            if i in rewrite else o
            for i, o in enumerate(tc.orders)
        ]
    else:
        engine_orders = tc.orders
```

d) Replace the engine call (lines 150-156):

```python
    try:
        geo = geography_phase(GeographyRequest(orders=engine_orders))
        situation = Situation(orders=geo.orders, switches=Switches())
        cr = conflict_game(
            situation,
            order_geo_info=geo.order_geo_info,
            convoy_graph=geo.convoy_graph,
        )
```

e) In `_compare_orders`, map the engine's B.4.2.9 demotion onto DipNet's failed-move expectation — after `act_s = act.succeeds` insert:

```python
        if exp.order == OrderType.mve and act.order == OrderType.hld:
            # engine demoted a geo-invalid move to hold; the unit did
            # not move -> compare as a failed move
            act_s = False
```

f) Delete the `if tc.has_convoy:` INCONCLUSIVE branch (lines 178-187) so diffs fall through to FAIL, and update the `evaluate_test_case` docstring (void strategy is now "selective rewrite + comparison skip").

g) Run `uv run ruff check test_data_pipeline/` — fix what YOUR edits introduced AND the **2 pre-existing findings** (one is an F841 in `run_dipnet_tests.py`, a file this task doesn't otherwise touch; fixing both here keeps the directory clean for the gate — and `run_dipnet_tests.py` is in this task's `git add` list below). While there, sweep the stale INCONCLUSIVE wording: the cluster-reporting sections in `run_dipnet_tests.py` become dead (leave the code — it degrades to empty sections — but drop wording claiming convoy cases are exempt), the `--verbose` argparse help still enumerates INCONCLUSIVE, and the `map_result` docstring in `mappings.py` says `["void"] → … (→ INCONCLUSIVE)` — update both (add `mappings.py` to the `git add` list). Run `uv run ruff format` on the touched files.

- [ ] **Step 4: Verify + measure the new baseline**

Run: `cd project && uv run python -m pytest test_data_pipeline/tests/ -v` → 5 PASS.
Run: `make -C project test-dipnet-quick` (evaluate printed counts, not exit code).
**Hard gate:** PASS ≥ 1545 of 1602, ERROR = 0, INCONCLUSIVE = 0, and both `1IbGdARWCes1lsqm_F1906M` and `_xh_i5Do4jzgx8yS_F1906M` gone from the FAIL list. Expected per the round-3 review emulation: **≈1561 PASS / ≈41 FAIL**, predominantly convoy plus a small non-convoy tail (measured 3, e.g. `h9QEPT6s5-Fi1WrV`) — ALL remaining FAILs regardless of class are Task 9's triage work list; do not chase them here. If PASS < 1545: STOP, do not commit, root-cause before proceeding.
**Record the numbers.** Standard gate → green.

- [ ] **Step 5: Commit**

```bash
git add project/test_data_pipeline/evaluator.py project/test_data_pipeline/dipnet_parser.py project/test_data_pipeline/run_dipnet_tests.py project/test_data_pipeline/mappings.py project/test_data_pipeline/tests/__init__.py project/test_data_pipeline/tests/test_evaluator_geography.py
git commit -m "feat(dipnet): adjudicate through geography; selective void rewrite

The evaluator bypassed geography (any surviving convoyer validated a
route; convoy diffs were blanket-exempted INCONCLUSIVE) and rewrote ALL
dataset-void orders to holds. DipNet 'void' is not one class: supports
of own-unit attacks still bounce third parties (the blanket rewrite
deleted that strength — root cause of both known FAILs 1IbGdARW…,
_xh_i5Do…), while statement-mismatch supports must NOT count (they are
unrepresentable in msup notation). Only void∩mismatch is rewritten now;
geo-invalid moves compare as failed moves (B.4.2.9 demotion vs DipNet
succeeds=False). Baseline after wiring (100 games): <numbers>."
```

---

### Task 4: cmove single source of truth — Engine konsumiert `cmove_candidates`

**Files:**
- Modify: `project/dipworkpy/conflict_game.py` (parser, nmove→cmove block at lines 119-124)
- Create: `project/tests/test_conflict_game_convoy_source.py`

**Interfaces:**
- Consumes: `ConvoyGraph.cmove_candidates: Set[int]` (positional indices into `situation.orders` == `geo.orders`).
- Produces: with `convoy_graph is not None`, parser promotes nmove→cmove **exactly** for indices in `cmove_candidates`; the raw con-scan remains only for `convoy_graph is None`. Closes the AGENTS.md Known Gap "cmove dual source of truth" (DECISION: honor the field).

**Honest scope note:** end-to-end misadjudication from the dual source is largely masked once geography is wired (GEO-006 invalidates stray convoyers → B.4.2.10 → they parse as `t_order.none`, so the legacy con-scan doesn't fire on them either). This task is consistency/robustness cleanup mandated by AGENTS.md, and its tests therefore assert at the `parser()` level (internal `t_world`), where the difference IS observable — plus end-to-end characterization.

- [ ] **Step 1: Write the tests**

Create `project/tests/test_conflict_game_convoy_source.py`:

```python
"""cmove promotion follows ConvoyGraph.cmove_candidates when a graph is present."""

from dipworkpy.conflict_game import conflict_game, parser
from dipworkpy.eval.eval_model import t_order
from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType, Situation


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current,
                 order=order, dest=dest)


def _world_with_geography(orders):
    geo = geography_phase(GeographyRequest(orders=orders))
    return parser(
        Situation(orders=geo.orders),
        order_geo_info=geo.order_geo_info,
        convoy_graph=geo.convoy_graph,
    )


def test_promotion_follows_cmove_candidates_only():
    """Fleet Nap->Apu 'convoyed' by ION: ION borders BOTH Nap and Apu,
    so the con order itself classifies valid and survives as
    t_order.convoy — but fleets are not convoyable (GEO-009 excludes
    them from cmove_candidates). Old parser: the con-scan promotes the
    fleet move to cmove (RED). New parser: candidates are authoritative,
    the move stays nmove (GREEN)."""
    world = _world_with_geography([
        mko("It", "F", "Nap", OrderType.mve, "Apu"),
        mko("It", "F", "ION", OrderType.con, "Nap"),
    ])
    assert world.get_field("Nap").order == t_order.nmove, world.get_field("Nap")


def test_real_convoy_is_promoted():
    world = _world_with_geography([
        mko("En", "A", "Lon", OrderType.mve, "Nor"),
        mko("En", "F", "NTH", OrderType.con, "Lon"),
    ])
    assert world.get_field("Lon").order == t_order.cmove, world.get_field("Lon")


def test_legacy_no_graph_path_unchanged():
    world = parser(Situation(orders=[
        mko("En", "A", "Lon", OrderType.mve, "Nor"),
        mko("En", "F", "NTH", OrderType.con, "Lon"),
    ]))
    assert world.get_field("Lon").order == t_order.cmove, world.get_field("Lon")


def test_end_to_end_valid_convoy_succeeds():
    orders = [
        mko("En", "A", "Lon", OrderType.mve, "Nor"),
        mko("En", "F", "NTH", OrderType.con, "Lon"),
    ]
    geo = geography_phase(GeographyRequest(orders=orders))
    cr = conflict_game(Situation(orders=geo.orders),
                       order_geo_info=geo.order_geo_info,
                       convoy_graph=geo.convoy_graph)
    lon = next(o for o in cr.orders if o.current == "Lon")
    assert lon.succeeds is None, cr
```

Check the exact import path of `t_order`/`parser` first (`grep -n "^def parser" project/dipworkpy/conflict_game.py`; `grep -n "class t_order" project/dipworkpy/eval/eval_model.py`) and adjust imports if they differ.

- [ ] **Step 2: Run — expect `test_promotion_follows_cmove_candidates_only` red.** Pre-verify the premise in one line: `ION` must classify as a VALID convoyer for `Nap→Apu` so its `t_order.convoy` reaches the con-scan (check: `geography_phase` on the two orders → the con order's `OrderGeoInfo.is_valid` is True). If geography unexpectedly invalidates it, swap in another fleet-move + flanking-convoyer pair where the con order stays valid (sea field adjacent to both ends) and document it. The other three tests are green pre-fix.

- [ ] **Step 3: Implement** — replace `conflict_game.py:119-124`:

```python
    # change nmoves to cmoves.
    # With a ConvoyGraph, geography's GEO-009 classification
    # (cmove_candidates, positional indices into situation.orders) is the
    # single source of truth. Without a graph (legacy callers), fall back
    # to the raw con-order scan.
    if convoy_graph is not None:
        for i, o in enumerate(situation.orders):
            if i in convoy_graph.cmove_candidates:
                field = world.get_field(o.current)
                if field and field.order in {t_order.nmove}:
                    log.debug("- changing nmove to cmove for field:%s (cmove_candidates)", field)
                    field.order = t_order.cmove
                    field.add_event("$cmove")
    else:
        for convoy_field, dest_field in world.get_fields_dests(lambda f: f.order in {t_order.convoy}):
            if dest_field.order in {t_order.nmove}:
                log.debug("- changing nmove to cmove for field:%s because of dest:%s", dest_field, convoy_field)
                dest_field.order = t_order.cmove
                dest_field.add_event("$cmove")
```

- [ ] **Step 4: Verify** — new tests PASS; standard gate green; `make test-dipnet-quick` counts ≥ Task-3 baseline.

- [ ] **Step 5: Commit**

```bash
git add project/dipworkpy/conflict_game.py project/tests/test_conflict_game_convoy_source.py
git commit -m "fix(engine): cmove promotion honors geography's cmove_candidates

parser promoted any move targeted by any con order to cmove while
geography's GEO-009 classification was carried into t_world but never
read (AGENTS.md known gap 'cmove dual source of truth'). With a graph
present the candidates set is now authoritative; no-graph callers keep
the legacy con-scan."
```

---

### Task 5: SYN-009 — fremde Einheit gestrichen, falscher Unit-Typ korrigiert

**Files:**
- Modify: `project/dipworkpy/syntax/rules.py`, `project/dipworkpy/syntax/service.py`
- Create: `project/tests/test_syntax_syn009.py`

**Interfaces:**
- Consumes: `unit_positions: Dict[str, Tuple[str, str]]` in `SyntaxRequest` (check `project/dipworkpy/syntax/model.py` for exact constructor fields/defaults before writing tests).
- Produces: nation mismatch → order STRUCK (SYN-009 correction; SYN-008 then hold-injects the real owner). utype mismatch with matching nation → order KEPT with utype corrected to the board's (SYN-009 diagnostic) — the stpsyr DATC files write unit letters loosely in places (verified in-file), and DipNet leniency matches. Also: SYN-005 doubles-counting must IGNORE orders that SYN-009 strikes, so a foreign order plus the owner's own order on the same unit doesn't kill both (the foreign order is simply ignored per DATC 6.A.6 intent).

- [ ] **Step 1: Failing tests**

Create `project/tests/test_syntax_syn009.py`:

```python
"""SYN-009: ordered unit must belong to the ordering nation; unit type
is advisory and gets corrected from the board."""

from dipworkpy.model import Order, OrderType
from dipworkpy.syntax.model import SyntaxRequest
from dipworkpy.syntax.service import syntax_phase


def test_foreign_unit_order_struck_and_owner_holds():
    req = SyntaxRequest(
        orders=[Order(nation="Ge", utype="F", current="Lon",
                      order=OrderType.mve, dest="NTH")],
        unit_positions={"Lon": ("En", "F")},
    )
    res = syntax_phase(req)
    assert [(o.nation, o.utype, o.current, o.order) for o in res.orders] == \
        [("En", "F", "Lon", OrderType.hld)]
    assert any(d.rule == "SYN-009" for d in res.diagnostics)


def test_wrong_utype_corrected_not_struck():
    req = SyntaxRequest(
        orders=[Order(nation="En", utype="A", current="Lon",
                      order=OrderType.mve, dest="NTH")],
        unit_positions={"Lon": ("En", "F")},
    )
    res = syntax_phase(req)
    assert [(o.nation, o.utype, o.current, o.order, o.dest) for o in res.orders] == \
        [("En", "F", "Lon", OrderType.mve, "NTH")]
    assert any(d.rule == "SYN-009" for d in res.diagnostics)


def test_foreign_order_does_not_double_strike_owners_order():
    """Foreign order + owner's own order on the same unit: SYN-005
    doubles-detection must not count the foreign one, so the owner's
    order survives."""
    req = SyntaxRequest(
        orders=[
            Order(nation="Ge", utype="F", current="Lon",
                  order=OrderType.mve, dest="NTH"),
            Order(nation="En", utype="F", current="Lon",
                  order=OrderType.mve, dest="ENG"),
        ],
        unit_positions={"Lon": ("En", "F")},
    )
    res = syntax_phase(req)
    assert [(o.nation, o.current, o.dest) for o in res.orders] == \
        [("En", "Lon", "ENG")]
```

(Adapt `SyntaxRequest` construction to its actual model fields — if `map`/`switches` are required without defaults, pass `map=MapRef()` / `switches=Switches()`.)

- [ ] **Step 2: Verify red** — `uv run python -m pytest tests/test_syntax_syn009.py -v` → all three FAIL (foreign order survives today; no utype correction exists; the doubles rule strikes the owner's own order alongside the foreign one).

- [ ] **Step 3: Implement**

`project/dipworkpy/syntax/rules.py`, after `has_unit_at_current` (line 38):

```python
def owner_mismatch(o: Order, unit_positions: dict) -> bool:
    """SYN-009 strike-half: order's nation differs from the unit owner."""
    unit = unit_positions.get(o.current)
    return unit is not None and o.nation != unit[0]


def utype_mismatch(o: Order, unit_positions: dict) -> bool:
    """SYN-009 correct-half: right owner, wrong unit letter."""
    unit = unit_positions.get(o.current)
    return unit is not None and o.nation == unit[0] and o.utype != unit[1]
```

`project/dipworkpy/syntax/service.py`: first change the doubles pre-count (line 33) so SYN-009-struck orders don't shadow the owner's real order:

```python
    counts = Counter(o.current for o in req.orders
                     if not rules.owner_mismatch(o, req.unit_positions))
```

then, inside the loop, after the SYN-006 check (lines 58-61) and before SYN-005:

```python
        if rules.owner_mismatch(o, req.unit_positions):
            diags.append(_diag("SYN-009", "correction",
                               f"unit at {o.current!r} belongs to "
                               f"{req.unit_positions[o.current][0]!r}, "
                               f"not {o.nation!r}", idx=i))
            continue
        if rules.utype_mismatch(o, req.unit_positions):
            corrected = o.model_copy(
                update={"utype": req.unit_positions[o.current][1]})
            diags.append(_diag("SYN-009", "correction",
                               f"unit type corrected to "
                               f"{corrected.utype!r} at {o.current!r}", idx=i))
            o = corrected
```

(the corrected `o` then continues through SYN-005 and into `survivors`).

- [ ] **Step 4: Verify** — new tests PASS; standard gate green (existing round/endpoint tests use consistent unit_positions, so no behavior change expected — if one fails, inspect whether it encoded the loophole). If a spec doc lists SYN-001..008 (`grep -rl "SYN-008" project/doc/ --exclude-dir=_design` — `doc/_design/` holds gitignored build mirrors, never edit those), add SYN-009 there NOW and include that doc file in THIS task's `git add` (don't leave it dangling for Task 11). Ordering note: the SYN-009 utype-correction runs after SYN-007; SYN-007 (`strict_unit_types`) is OFF by default, so no conflict in these suites — if it is ever switched on, correction should precede it.

- [ ] **Step 5: Commit**

```bash
git add project/dipworkpy/syntax/rules.py project/dipworkpy/syntax/service.py project/tests/test_syntax_syn009.py
# plus the SYN-rule-table doc file, if Step 4 updated one
git commit -m "feat(syntax): SYN-009 — foreign-unit orders struck, unit letter corrected

has_unit_at_current only checked presence: a nation could order another
nation's unit and it executed (DATC 6.A.6). Nation mismatch now strikes
(SYN-008 hold-injects the real owner); a wrong unit letter from the
right owner is corrected in place because the stpsyr DATC files treat
it as advisory (6.B.13)."
```

---

### Task 6: stpsyr-Parser neu — Kommentare, Phasen, Builds/Disbands, H-Notation, Superfields

**Files:**
- Modify: `project/tests_from_stpsyr/stpsyr_test_runner.py` (parser half: `TestCase`, new `Phase`, `parse_territory_name`, `parse_order`, `parse_file`)
- Create: `project/tests_from_stpsyr/test_stpsyr_parser.py`

**Interfaces:**
- Consumes: `test_data_pipeline.mappings.convert_territory` (canonical territory table; collapses coast suffixes to superfields — `SPA/SC → Spa`).
- Produces (for Task 7):

```python
@dataclass
class Phase:
    orders: List[Order]                 # movement orders (may be empty for adjustment phases)
    builds: List[Tuple[str, str, str]]  # (nation, utype, territory)  from "B F bre"
    disbands: List[str]                 # territory                   from "D hel"

@dataclass
class TestCase:
    number: int
    title: str
    phases: List[Phase]
    expected_results: Dict[str, str]  # superfield -> "Fleet England"|"Army Italy"|"empty"
```

**Format facts (verified on disk):** 93 `# N.` headers, **92 parseable** (a=12, b=12, c=7, d=33, e=15, f=13); the only stub is 6.b case 14 (header + `// TODO (pending builds)`, no orders/results) — the parser must WARN about dropped stubs, not silently swallow them. Blank line between order blocks = phase boundary. `//` lines are comments (currently corrupt the state machine — 4 cases lost that way; the 5th "missing" case is the 6.b.14 stub). Explicit hold notation exists: `    A tri H` (6 lines in datc-6.d.txt:161/169/192/260/417/468) and support-to-hold may be written `S A tri H` — trailing `H` tokens must be handled, not crash territory lookup. Build/disband lines: `B F bre` (6.f:73,180), `D hel` (6.e:76,128), `B A kie`/`B A ber` (6.e:413-414). Coast suffixes (`spa/nc`, `bul/ec`, `stp/sc`) collapse to superfields — **the whole stpsyr lane is superfield-only** (engine constraint; coast-fidelity cases are Task 10 bucket B). `(via convoy)` is stripped — GEO-009 recovers convoy intent from companion con orders; exception: 6.d case 32 deliberately omits the fleet, the move then classifies geo-invalid → holds, which matches the case's no-convoy intent (Task 10 watchlist).

- [ ] **Step 1: Write parser tests first**

Create `project/tests_from_stpsyr/test_stpsyr_parser.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dipworkpy.model import OrderType
from stpsyr_test_runner import StpsyrTestRunner

BASE = os.path.dirname(os.path.abspath(__file__))


def _parse(name):
    return StpsyrTestRunner().parse_file(os.path.join(BASE, name))


def test_case_counts_match_parseable_cases():
    # 93 headers on disk; 6.b case 14 is a header-only TODO stub.
    expected = {"datc-6.a.txt": 12, "datc-6.b.txt": 12, "datc-6.c.txt": 7,
                "datc-6.d.txt": 33, "datc-6.e.txt": 15, "datc-6.f.txt": 13}
    for fname, count in expected.items():
        cases = _parse(fname)
        assert len(cases) == count, f"{fname}: {len(cases)} != {count}"


def test_multiphase_case_is_split():
    # 6.a case 5 "Move to own sector with convoy": 2 movement phases
    cases = _parse("datc-6.a.txt")
    case5 = next(c for c in cases if c.number == 5)
    assert len(case5.phases) == 2
    assert len(case5.phases[0].orders) == 4
    assert len(case5.phases[1].orders) == 5


def test_msup_dest_is_supported_units_start():
    # "tyr S ven-tri" -> msup with dest=Ven (unit start), NOT Tri
    cases = _parse("datc-6.a.txt")
    case5 = next(c for c in cases if c.number == 5)
    msups = [o for p in case5.phases for o in p.orders if o.order == OrderType.msup]
    assert any(o.current == "Tyr" and o.dest == "Ven" for o in msups), msups


def test_explicit_hold_H_notation():
    # datc-6.d.txt contains '    A tri H' style holds (e.g. line 161)
    cases = _parse("datc-6.d.txt")
    holds = [o for c in cases for p in c.phases for o in p.orders
             if o.order == OrderType.hld]
    assert holds, "explicit 'X H' holds must parse as hld, not vanish"


def test_coast_suffix_collapses_to_superfield():
    r = StpsyrTestRunner()
    assert r.parse_territory_name("spa/nc") == "Spa"
    assert r.parse_territory_name("spa/sc") == "Spa"
    assert r.parse_territory_name("bul/ec") == "Bul"
    assert r.parse_territory_name("stp/sc") == "Pet"


def test_canonical_renames():
    r = StpsyrTestRunner()
    assert r.parse_territory_name("lvp") == "Lpl"
    assert r.parse_territory_name("sev") == "Seb"
    assert r.parse_territory_name("stp") == "Pet"
    assert r.parse_territory_name("mao") == "MID"
    assert r.parse_territory_name("nao") == "NAT"
    assert r.parse_territory_name("nwg") == "NWS"
    assert r.parse_territory_name("nwy") == "Nor"
    assert r.parse_territory_name("bal") == "BAS"
    assert r.parse_territory_name("lyo") == "LYO"
    assert r.parse_territory_name("aeg") == "AEG"


def test_builds_and_disbands_parsed():
    cases = _parse("datc-6.e.txt")
    with_disband = [c for c in cases if any(p.disbands for p in c.phases)]
    assert with_disband, "expected at least one case with 'D hel'"
    d = next(p for c in with_disband for p in c.phases if p.disbands)
    assert d.disbands == ["HEL"]
```

- [ ] **Step 2: Run — all new tests fail** (`cd project && uv run python -m pytest tests_from_stpsyr/test_stpsyr_parser.py -v`; collection itself may fail until the dataclasses exist — that counts as red).

- [ ] **Step 3: Implement the parser rewrite**

In `stpsyr_test_runner.py`:

a) Import `from test_data_pipeline.mappings import convert_territory` at module top — **BELOW the `sys.path.insert(...)` lines from Task 1** (the import only resolves once `project/` is on the path; placing it above crashes the script). Replace `parse_territory_name`:

```python
    def parse_territory_name(self, territory: str) -> str:
        """stpsyr name -> DipworkPy superfield. Coast suffixes collapse
        (engine and board are superfield-only; see Task-10 bucket B)."""
        return convert_territory(territory.strip())
```

(`convert_territory` upper-cases internally, maps `SPA/SC → Spa`, raises `KeyError` on unknown names — a loud parse error is wanted.) Delete the old `territory_map` dict.

b) Rewrite `parse_order` to handle trailing `H` tokens and keep the msup fix:

```python
    def parse_order(self, line: str, nation: str) -> Optional[Order]:
        line = line.strip()
        if not line:
            return None
        parts = line.split()
        if len(parts) < 2:
            return None
        unit_type = parts[0]  # A or F
        order_text = " ".join(parts[1:])
        if "(via convoy)" in order_text:
            order_text = order_text.replace("(via convoy)", "").strip()

        if " S " in order_text:  # support
            lhs, support_text = order_text.split(" S ", 1)
            current = self.parse_territory_name(lhs)
            if support_text.startswith("A ") or support_text.startswith("F "):
                support_text = support_text[2:]
            tokens = support_text.split()
            if tokens and tokens[-1] == "H":     # "S tri H" == support-to-hold
                tokens = tokens[:-1]
            support_text = " ".join(tokens)
            if "-" in support_text:              # support-to-move "apu-ven"
                start, _dest = support_text.split("-", 1)
                return Order(nation=nation, utype=unit_type,
                             current=current, order=OrderType.msup,
                             dest=self.parse_territory_name(start))
            if support_text:
                return Order(nation=nation, utype=unit_type,
                             current=current, order=OrderType.hsup,
                             dest=self.parse_territory_name(support_text))
            return None

        if " C " in order_text:  # convoy — dest = convoyed unit's start
            lhs, convoy_info = order_text.split(" C ", 1)
            current = self.parse_territory_name(lhs)
            if convoy_info.startswith("A ") or convoy_info.startswith("F "):
                convoy_info = convoy_info[2:]
            dest = (self.parse_territory_name(convoy_info.split("-")[0])
                    if "-" in convoy_info else current)
            return Order(nation=nation, utype=unit_type, current=current,
                         order=OrderType.con, dest=dest)

        tokens = order_text.split()
        if tokens and tokens[-1] == "H":         # "lon H" == explicit hold
            tokens = tokens[:-1]
        order_text = " ".join(tokens)

        if "-" in order_text:                    # move "lon-pic" / "mao-spa/nc"
            start, dest = order_text.split("-", 1)
            return Order(nation=nation, utype=unit_type,
                         current=self.parse_territory_name(start),
                         order=OrderType.mve,
                         dest=self.parse_territory_name(dest))

        if order_text:                           # bare territory == hold
            return Order(nation=nation, utype=unit_type,
                         current=self.parse_territory_name(order_text),
                         order=OrderType.hld)
        return None
```

c) Rewrite `parse_file` as a phase-aware state machine (replaces the whole method):

```python
    def parse_file(self, filename: str) -> List["TestCase"]:
        test_cases: List[TestCase] = []
        cur: Optional[TestCase] = None
        phase = Phase(orders=[], builds=[], disbands=[])
        nation = ""

        def close_phase():
            nonlocal phase
            if phase.orders or phase.builds or phase.disbands:
                assert cur is not None
                cur.phases.append(phase)
            phase = Phase(orders=[], builds=[], disbands=[])

        def close_case():
            nonlocal cur
            if cur is not None:
                close_phase()
                if cur.phases and cur.expected_results:
                    test_cases.append(cur)
                else:
                    print(f"⚠️  dropping stub/incomplete case "
                          f"{cur.number}. {cur.title}")
            cur = None

        with open(filename, "r") as f:
            for raw in f:
                line = raw.rstrip("\n")
                stripped = line.strip()
                if stripped.startswith("/"):        # '//' comment (lib.rs)
                    continue
                if line.startswith("# "):           # case header
                    close_case()
                    header = line[2:].strip()
                    if ". " in header:
                        num_str, title = header.split(". ", 1)
                        try:
                            cur = TestCase(number=int(num_str), title=title,
                                           phases=[], expected_results={})
                        except ValueError:
                            cur = None
                    continue
                if cur is None:
                    continue
                if not stripped:                    # blank line = phase end
                    close_phase()
                    continue
                if line.startswith("    "):         # order / build / disband
                    parts = stripped.split()
                    if parts[0] == "B" and len(parts) == 3:
                        phase.builds.append(
                            (nation, parts[1],
                             self.parse_territory_name(parts[2])))
                    elif parts[0] == "D" and len(parts) == 2:
                        phase.disbands.append(
                            self.parse_territory_name(parts[1]))
                    else:
                        order = self.parse_order(line, nation)
                        if order:
                            phase.orders.append(order)
                    continue
                if ":" in line:                     # "lon: Fleet England"
                    territory, expected = line.split(":", 1)
                    cur.expected_results[
                        self.parse_territory_name(territory)] = expected.strip()
                    continue
                nation = self.parse_nation_name(stripped)   # nation line
        close_case()
        return test_cases
```

Add the `Phase` dataclass next to `TestCase` per the Interfaces block; the old `TestCase.orders`/`expected_results` flat fields are replaced.

**Note:** `run_test_case` still consumes the OLD shape and will be rewritten in Task 7 — to keep the runner importable between the two tasks, adapt it minimally in THIS task (iterate `test_case.phases[0].orders` if it must run at all) or, simpler, land Tasks 6+7 as one commit if the intermediate state is broken. Preferred: implement Task 6, run only the parser pytest (the runner script itself may be temporarily non-functional), and commit both tasks' runner file changes together at the end of Task 7. The parser tests commit separately here if the runner still executes; otherwise fold this commit into Task 7's.

- [ ] **Step 4: Verify** — `uv run python -m pytest tests_from_stpsyr/test_stpsyr_parser.py -v` → all green. Standard gate → green.

- [ ] **Step 5: Commit** (or fold into Task 7 per the note above)

```bash
git add project/tests_from_stpsyr/stpsyr_test_runner.py project/tests_from_stpsyr/test_stpsyr_parser.py
git commit -m "fix(stpsyr): phase-aware DATC parser with canonical territory map

Five parser defects hid most of the suite: '//' comments containing ': '
flipped the state machine into result-collection (4 cases dropped; a
5th missing case is a header-only TODO stub the new parser warns about);
multi-phase cases were flattened (55/88 crashed on duplicate fields);
msup dest pointed at the move target instead of the supported unit's
start; explicit 'X H' hold notation crashed territory lookup; the
ad-hoc territory map broke on unmapped seas. Territory names now come
from test_data_pipeline.mappings (superfield-only, coast fidelity
documented as out of scope)."
```

---

### Task 7: stpsyr-Runner — Standard-Board, round_full pro Phase, echte Verifikation

**Files:**
- Modify: `project/tests_from_stpsyr/stpsyr_test_runner.py` (runner half: `run_test_case`, `run_file`, `main`)
- Modify: `project/Makefile:35-37` — only the `##` help text: "Run full STPSYR DATC runner (verifying)".

**Interfaces:**
- Consumes: `round_full(RoundRequest(orders=…, unit_positions=…)) -> RoundResult`, `RoundResult.conflict.resolution: ConflictResolution` (from `dipworkpy.round.orchestrator`); `Phase`/`TestCase` from Task 6; SYN-009 from Task 5.
- Produces: per-case verdict PASS / FAIL / ERROR with final-board comparison; summary per file + overall; exit 0 only when FAIL+ERROR == 0 (and ≥1 test found).

**Why round_full:** the stpsyr cases start from the **standard 1901 opening position** — 6.A.6 orders England's fleet as Germany (needs board + SYN-009); unordered board units must hold-default (SYN-008); doubles must strike (SYN-005), not crash.

- [ ] **Step 1: Implement board + loop**

Add to `stpsyr_test_runner.py` (module level):

```python
STANDARD_START: Dict[str, Tuple[str, str]] = {
    # Austria            # England            # France
    "Vie": ("Au", "A"),  "Lon": ("En", "F"),  "Par": ("Fr", "A"),
    "Bud": ("Au", "A"),  "Edi": ("En", "F"),  "Mar": ("Fr", "A"),
    "Tri": ("Au", "F"),  "Lpl": ("En", "A"),  "Bre": ("Fr", "F"),
    # Germany            # Italy              # Turkey
    "Ber": ("Ge", "A"),  "Rom": ("It", "A"),  "Con": ("Tu", "A"),
    "Mun": ("Ge", "A"),  "Ven": ("It", "A"),  "Smy": ("Tu", "A"),
    "Kie": ("Ge", "F"),  "Nap": ("It", "F"),  "Ank": ("Tu", "F"),
    # Russia (F StP/SC -> superfield Pet)
    "Mos": ("Ru", "A"), "War": ("Ru", "A"), "Seb": ("Ru", "F"), "Pet": ("Ru", "F"),
}


def apply_resolution(board, resolution):
    """Advance the board one movement phase.

    Returns (new_board, dislodged_units); dislodged_units maps
    field -> (nation, utype) for units knocked off the board this phase
    — the NEXT block may be their retreat phase (see run_test_case).

    succeeds: None == success, False == failed (never truth-test).
    A dislodged unit's field may simultaneously be the destination of
    the successful move that dislodged it — removal happens before
    arrivals are placed, so that is handled naturally.
    """
    moved = {}
    vacated = set()
    dislodged = {}
    for r in resolution.orders:
        if r.order == OrderType.mve and r.succeeds is None:
            vacated.add(r.current)
            moved[r.dest] = (r.nation, r.utype)
        if r.dislodged is True:
            dislodged[r.current] = (r.nation, r.utype)
    new_board = {f: u for f, u in board.items()
                 if f not in vacated and f not in dislodged}
    new_board.update(moved)
    return new_board, dislodged


def expected_matches(board, territory, expectation, parse_nation_name):
    if expectation.lower() == "empty":
        return territory not in board
    parts = expectation.split()           # "Fleet England"
    if len(parts) != 2:
        return False
    utype = {"Fleet": "F", "Army": "A"}.get(parts[0])
    nation = parse_nation_name(parts[1])
    return board.get(territory) == (nation, utype)
```

Replace `run_test_case`:

```python
    def run_test_case(self, test_case, verbose=False):
        """Returns 'PASS' | 'FAIL' | 'ERROR'."""
        from collections import Counter

        from dipworkpy.round.orchestrator import RoundRequest, round_full

        board = dict(STANDARD_START)
        dislodged = {}
        try:
            for phase in test_case.phases:
                # builds/disbands are their own (winter) blocks in the
                # files and precede the next movement block
                for terr in phase.disbands:
                    board.pop(terr, None)
                for nation, utype, terr in phase.builds:
                    board[terr] = (nation, utype)
                if not phase.orders:
                    continue
                if dislodged and all(
                        dislodged.get(o.current) == (o.nation, o.utype)
                        for o in phase.orders):
                    # Retreat phase: every order references a unit that
                    # was just dislodged (e.g. datc-6.f.7 'F nth-bel').
                    # Naive application, no retreat-conflict engine:
                    # retreat-move to an empty, uncontested field
                    # succeeds; everything else disbands (the unit is
                    # already off the board).
                    dest_counts = Counter(
                        o.dest for o in phase.orders
                        if o.order == OrderType.mve and o.dest)
                    for o in phase.orders:
                        if (o.order == OrderType.mve and o.dest
                                and o.dest not in board
                                and dest_counts[o.dest] == 1):
                            board[o.dest] = (o.nation, o.utype)
                    dislodged = {}
                    continue
                rr = round_full(RoundRequest(orders=phase.orders,
                                             unit_positions=board))
                board, dislodged = apply_resolution(board,
                                                    rr.conflict.resolution)
        except Exception as e:
            print(f"! ERROR test {test_case.number} ({test_case.title}): {e}")
            return "ERROR"

        mismatches = []
        for territory, expectation in test_case.expected_results.items():
            if not expected_matches(board, territory, expectation,
                                    self.parse_nation_name):
                mismatches.append(
                    f"{territory}: expected {expectation!r}, "
                    f"board has {board.get(territory)}")
        if mismatches:
            print(f"- FAIL test {test_case.number} ({test_case.title})")
            for m in mismatches:
                print(f"    {m}")
            return "FAIL"
        if verbose:
            print(f"+ PASS test {test_case.number} ({test_case.title})")
        return "PASS"
```

Update `run_file`/`main`: count PASS/FAIL/ERROR per file and overall; print a summary block; `main` returns `0` only if `failed + errors == 0` and `total > 0`. Delete the old "executed successfully" wording — say PASS/FAIL/ERROR.

**Known limitations (write into the module docstring):** (1) Retreat phases are applied NAIVELY: a block counts as a retreat phase only when every order references a just-dislodged unit (datc-6.f.7 has exactly one such block); single uncontested retreat-moves succeed, everything else disbands — there is no retreat-CONFLICT resolution (engine gap, AGENTS.md Roadmap #3). (2) Superfield-only board: coast-specific expectations in 6.b adjudicate approximately (Task 10 bucket B).

- [ ] **Step 2: Verify**

Run: `cd project && uv run python tests_from_stpsyr/stpsyr_test_runner.py 2>&1 | tail -30`
Expected: **92 cases execute, ERROR = 0** (any ERROR is a real parse/engine defect — investigate before proceeding; `LookupError: fieldname twice` must be gone). Spot-check four verdicts by hand: 6.a.1 (illegal `lon-pic` → geography invalidates → `lon: Fleet England` PASS), 6.a.6 (foreign order → SYN-009 → PASS), 6.c.5 (multi-phase — board carries between phases), 6.f.7 (retreat phase: dislodged NTH fleet retreats to Bel → `bel: Fleet England` PASS). Do NOT use 6.a.5 as a positive spot-check — the self-convoy `tri-tri` case is expected to misbehave (`convoy_route_exists` returns True for start==dest without any convoyer; Task 10 watchlist). **Record PASS/FAIL/ERROR — this is the honest stpsyr baseline.** FAILs are Task 10's triage input, NOT a blocker here.

Run: `make -C project test-stpsyr-full` → same numbers, exit code correct.
Standard gate → green.

- [ ] **Step 3: Commit**

```bash
git add project/tests_from_stpsyr/stpsyr_test_runner.py project/tests_from_stpsyr/test_stpsyr_parser.py project/Makefile
git commit -m "feat(stpsyr): verify final board state through the full round pipeline

'pass' previously meant 'did not throw' — expected results were parsed
and discarded (TODO since the runner was written), and 55 of 88 cases
crashed on flattened phases. Cases now start from the standard 1901
position and run per-phase through round_full (syntax SYN-005/008/009,
geography convoy graph + move legality, conflict resolution), then the
final board is compared against the files' expectations.
Baseline: <PASS/FAIL/ERROR> of 92."
```

---

### Task 8: Regressionstests für die zwei Ex-DipNet-FAILs

**Files:**
- Create: `project/test_data_pipeline/tests/fixtures/` (two JSON fixtures) + `project/test_data_pipeline/tests/test_dipnet_regressions.py`
- Create: `project/tests/test_conflict_chain_characterization.py`

**Interfaces:**
- Consumes: Task 3 (both cases PASS through the evaluator now — Task 3's gate verified that).
- Produces: the two dataset cases are pinned as offline regression tests (no 2.7 GB dataset needed at test time), plus two engine-level characterization tests for the underlying rule behaviors.

- [ ] **Step 1: Extract fixtures**

One-off extraction (run from the session scratchpad, NOT saved into the repo): for each of `1IbGdARWCes1lsqm`/`F1906M` and `_xh_i5Do4jzgx8yS`/`F1906M`, load the game line from `../testdata/diplomacy-research/standard_no_press.jsonl`, run it through `test_data_pipeline.dipnet_parser` to a `DwpcrTestCase`, and dump `{id, orders, expected, has_convoy, has_void, void_order_indices, mismatch_support_indices, source_phase, source_game}` as JSON (Pydantic `Order`/`OrderResult` via `.model_dump()`) into `project/test_data_pipeline/tests/fixtures/<id>.json`. Keep each file < 30 KB; the two JSON files are the only new artifacts under the repo.

- [ ] **Step 2: Write the fixture-driven test**

`project/test_data_pipeline/tests/test_dipnet_regressions.py`:

```python
"""The two DipNet cases that failed while the evaluator rewrote void
orders to holds (fixed in the geography-wiring change). Pinned offline."""

import json
import os

import pytest

from dipworkpy.model import Order, OrderResult

from test_data_pipeline.dipnet_parser import DwpcrTestCase
from test_data_pipeline.evaluator import TestResult, evaluate_test_case

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.mark.parametrize("case_id", [
    "1IbGdARWCes1lsqm_F1906M",
    "_xh_i5Do4jzgx8yS_F1906M",
])
def test_ex_fail_case_passes(case_id):
    with open(os.path.join(FIXTURES, case_id + ".json")) as f:
        raw = json.load(f)
    tc = DwpcrTestCase(
        id=raw["id"],
        orders=[Order(**o) for o in raw["orders"]],
        expected=[OrderResult(**r) for r in raw["expected"]],
        has_convoy=raw["has_convoy"],
        has_void=raw["has_void"],
        source_phase=raw["source_phase"],
        source_game=raw["source_game"],
        void_order_indices=raw["void_order_indices"],
        mismatch_support_indices=raw["mismatch_support_indices"],
    )
    result = evaluate_test_case(tc, keep_details=True)
    assert result.result == TestResult.PASS, result.diffs
```

Run: `cd project && uv run python -m pytest test_data_pipeline/tests/test_dipnet_regressions.py -v` → 2 PASS (they pass since Task 3; this pins them offline).

- [ ] **Step 3: Engine-level characterization tests**

`project/tests/test_conflict_chain_characterization.py` — these scenarios pass on today's engine (verified); they pin the rule behaviors the two dataset cases depend on, so future eval-phase work can't silently regress them:

```python
"""Characterization: rule behaviors behind the two ex-DipNet-FAIL cases.

Both scenarios adjudicate correctly on the bare engine; the dataset
failures came from the evaluator's (removed) void->hld rewrite.
"""

from dipworkpy.conflict_game import conflict_game
from dipworkpy.model import Order, OrderType, Situation


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current,
                 order=order, dest=dest)


def _by_current(orders):
    cr = conflict_game(Situation(orders=orders))
    return {o.current: o for o in cr.orders}


def test_supported_attack_beats_weak_attack_into_vacated_field():
    """Tyr->Tri (str 3) vs Bud->Tri (str 1) while Tri->Ser leaves:
    Tyr enters, Bud bounces, the vacating unit is not dislodged."""
    by = _by_current([
        mko("It", "A", "Tri", OrderType.mve, "Ser"),
        mko("It", "A", "Tyr", OrderType.mve, "Tri"),
        mko("It", "A", "Ven", OrderType.msup, "Tyr"),
        mko("It", "F", "ADR", OrderType.msup, "Tyr"),
        mko("Ru", "A", "Bud", OrderType.mve, "Tri"),
    ])
    assert by["Tri"].succeeds is None and by["Tri"].dislodged is None, by["Tri"]
    assert by["Tyr"].succeeds is None, by["Tyr"]
    assert by["Bud"].succeeds is False, by["Bud"]


def test_no_self_dislodgement_in_bounce_chain():
    """Fr Ber->Mun (str 3) vs Au Tyr->Mun (str 2) while Fr Mun->Sil
    bounces: France may not dislodge its own unit; its strength still
    bounces Tyr; the chain behind Tyr bounces too."""
    by = _by_current([
        mko("Au", "A", "Pie", OrderType.mve, "Tyr"),
        mko("Au", "A", "Tus", OrderType.mve, "Pie"),
        mko("Au", "A", "Tyr", OrderType.mve, "Mun"),
        mko("Au", "A", "Boh", OrderType.msup, "Tyr"),
        mko("Au", "A", "Pru", OrderType.mve, "Ber"),
        mko("Au", "A", "Sil", OrderType.msup, "Pru"),
        mko("Fr", "A", "Ber", OrderType.mve, "Mun"),
        mko("Fr", "A", "Mun", OrderType.mve, "Sil"),
        mko("Fr", "A", "Kie", OrderType.msup, "Ber"),
        mko("Fr", "A", "Ruh", OrderType.msup, "Ber"),
    ])
    assert by["Mun"].dislodged is None, by["Mun"]
    for f in ("Pie", "Tus", "Tyr", "Ber", "Mun", "Pru"):
        assert by[f].succeeds is False, (f, by[f])
```

Run: `cd project && uv run python -m pytest tests/test_conflict_chain_characterization.py -v` → 2 PASS immediately (characterization, not TDD — the point is pinning).

- [ ] **Step 4: Standard gate → green. Commit**

```bash
git add project/test_data_pipeline/tests/fixtures/1IbGdARWCes1lsqm_F1906M.json \
        project/test_data_pipeline/tests/fixtures/_xh_i5Do4jzgx8yS_F1906M.json \
        project/test_data_pipeline/tests/test_dipnet_regressions.py \
        project/tests/test_conflict_chain_characterization.py
git commit -m "test: pin the two ex-DipNet-FAIL cases offline

The dataset cases failed only through the evaluator's void->hld
rewrite; the engine itself adjudicates both correctly. JSON fixtures
keep them testable without the 2.7GB dataset, and engine-level
characterization tests pin the two rule behaviors involved
(supported attack into a vacated field; self-dislodgement
prohibition in a bounce chain)."
```

---

### Task 9: DipNet-Convoy-Triage — verbleibende FAILs klassifizieren, Engine-Bugs fixen

**Files:**
- Create: `project/doc/DIPNET_CONVOY_TRIAGE.md`
- Modify: engine files per root cause; regression tests appended to `project/tests/` (engine) or `project/test_data_pipeline/tests/` (mapping)

**Interfaces:**
- Consumes: Task 3 baseline (its recorded FAIL list) + Tasks 4/8.
- Produces: every FAIL on the 100-game sample classified into exactly one bucket: **(A) engine bug** — fixed with regression test; **(B) VIA-intent loss** — counted, documented, NOT fixed here; **(C) dataset/mapping artifact** — documented. End state: `make test-dipnet-quick` FAILs consist only of documented B/C cases.

**Bucket B background:** `mappings.py:164-168` silently drops DipNet's `VIA` suffix; `Order` has no `via_convoy` field (GEO-010 explicitly deferred, `geo_model.py:178-181`). An adjacent move flagged VIA whose convoy fails is "no convoy" (`succeeds=False`) for DipNet but a successful land move for our engine. Known class — goes to AGENTS.md as a sized follow-up (case count from this triage), not fixed in this plan.

- [ ] **Step 1: Work list**

```bash
cd project && uv run python -m test_data_pipeline.run_dipnet_tests \
  --max-games 100 --with-failures \
  ../testdata/diplomacy-research/standard_no_press.jsonl \
  > /tmp/dipnet-triage.txt 2>&1
grep -c "^--- - FAIL" /tmp/dipnet-triage.txt
```

- [ ] **Step 2: Classify every FAIL**

Per failure block: (1) any diffing order convoy/VIA-related? Check the raw dataset line (`grep <gameid> ../testdata/diplomacy-research/standard_no_press.jsonl | uv run python -m json.tool`) for `VIA` in the original order → bucket B. (2) Re-adjudicate by hand against DATC (`testdata/datc-v3/DATC_v3_0.html`); dataset right + engine wrong → bucket A. (3) Mapping/void-comparison artifact → bucket C. One table row per case in `project/doc/DIPNET_CONVOY_TRIAGE.md`: `| case_id | bucket | diffing orders | one-line diagnosis |`. **Known starting point:** the ≈3 non-convoy FAILs (`h9QEPT6s5-Fi1WrV_F1910M`, `kLq1Qi6MqjKKDd4G_F1917M`, `5M65XaqXlieNDQVV_S1907M`) are the live own-unit-attack void-support family — the engine appears to let a supported own attack dislodge the own unit in a bounce chain where the dataset says bounce/no-dislodge (DATC 6.D self-dislodgement family). Strong bucket-A candidates: adjudicate by hand first; if confirmed, that is exactly the solver-bug class this plan exists to fix.

- [ ] **Step 3: Fix bucket-A bugs**

Group bucket-A by root cause (plausible area per AGENTS.md: `eval_k1.py` one-shot dislodged-convoyer restriction). Per cause: reduced failing engine test (`mko`-pattern, in `project/tests/`) → REQUIRED SUB-SKILL superpowers:systematic-debugging (instrumentation: `__log__()` on all internal models, `logging.getLogger("dipworkpy").setLevel(logging.DEBUG)` in a scratch script) → minimal fix → standard gate + `make test-dipnet-quick` counts improve. **Convoy-paradox cases needing the k1 fixpoint (AGENTS.md Roadmap #1) are OUT OF SCOPE — bucket them B with a Roadmap-#1 reference.** One commit per root cause citing case IDs.

- [ ] **Step 4: Close out**

`make -C project test-dipnet-quick`: every remaining FAIL has a triage-table row (bucket B/C). Then one wider sample — deliberately through the PARALLEL path so it gets exercised once post-wiring: `uv run python -m test_data_pipeline.run_dipnet_tests --workers 8 --max-games 1000 ../testdata/diplomacy-research/standard_no_press.jsonl`; spot-check its counts against a small sequential run, then append the summary to the triage doc (new failure classes: add rows; fix only cheap bucket-A; otherwise documented follow-up).

- [ ] **Step 5: Commit** (triage doc + fixes, per-cause commits from Step 3 already made)

```bash
git add project/doc/DIPNET_CONVOY_TRIAGE.md
git commit -m "docs(dipnet): triage table for post-wiring failures

Every remaining FAIL on the 100-game sample is classified (engine bug /
VIA-intent loss / dataset artifact); engine bugs are fixed with pinned
regressions, VIA loss is sized for the GEO-010 follow-up."
```

---

### Task 10: stpsyr-Triage — Adjudication-FAILs klassifizieren, Solver-Bugs fixen

**Files:**
- Create: `project/doc/STPSYR_TRIAGE.md`
- Modify: engine files per root cause; regression tests in `project/tests/`

**Interfaces:**
- Consumes: Task 7 baseline (PASS/FAIL/ERROR of 92).
- Produces: every FAIL classified: **(A) engine bug** → fixed + regression test in `project/tests/`; **(B) runner/board-model limitation** (coast fidelity in 6.b, retreat-move phases, convoy-paradox fixpoint) → documented; **(C) stpsyr-file deviation from DATC** → documented, mismatch accepted.

- [ ] **Step 1: Work list** — `make -C project test-stpsyr-full 2>&1 | tee /tmp/stpsyr-triage.txt`; every `- FAIL` block is one row.

- [ ] **Step 2: Classify** — table in `project/doc/STPSYR_TRIAGE.md`. Priorities: **6.e (15 convoy cases) and 6.f (13 beleaguered/complex cases) first** — they are the convoy-correctness benchmark this plan exists for. Cross-check bucket-C candidates: the files mark deliberate DATC deviations — find them all via `grep -n "DIFFERS FROM DATC" project/tests_from_stpsyr/datc-6.*.txt` (3 markers: 6.b twice, 6.d once) and match each to its case. Known watchlist rows to check explicitly: 6.a.5 self-convoy (`convoy_route_exists` returns True for start==dest without any convoyer — suspicious, may adjudicate wrong for the wrong reason), 6.b coast cases (superfield approximation), convoy-paradox family (bucket B → Roadmap #1).

- [ ] **Step 3: Fix bucket-A engine bugs** — same discipline as Task 9 Step 3. Validation after each fix: standard gate + `make test-dipnet-quick` counts hold-or-improve + `make test-stpsyr-full` counts improve.

- [ ] **Step 4: Commits** — per root cause; final commit adds the triage doc (same pattern as Task 9 Step 5).

---

### Task 11: Status-Docs + Memory aktualisieren

**Files:**
- Modify: `CLAUDE.md` (Project Overview: replace "DipNet = 96.4% …" and the geography-not-yet-wired caveat with post-plan measured numbers), `AGENTS.md` (Roadmap #5 → done with numbers; Known Gaps: remove "cmove dual source of truth" + "DipNet evaluator not geography-aware"; ADD: GEO-010/VIA follow-up with measured case count, GEO-004 msup fix note, SYN-009; update stpsyr status), any doc listing SYN/GEO rule tables (`grep -rl "SYN-008\|GEO-009" project/doc/`).
- Modify: auto-memory `MEMORY.md` + memory files (DipNet numbers, stpsyr runner is now verifying, void-rewrite removal).

- [ ] **Step 1:** Update docs with final measured numbers (never round up; state sample sizes: "100 games / 1602 cases", "92 stpsyr cases").
- [ ] **Step 2:** Final validation: `make -C project check` AND `cd project && uv run python -m pytest tests/ test_data_pipeline/tests/ tests_from_stpsyr/test_stpsyr_parser.py -q` AND `make -C project test-dipnet-quick` AND `make -C project test-stpsyr-full` — paste all summaries into the commit body. Reminder: the two suite targets exit NONZERO by design while documented bucket-B/C FAILs remain — judge them by their printed counts matching the Task 9/10 triage tables, not by exit code.
- [ ] **Step 3: Commit**

Run `git status --short project/doc/` first and stage ONLY the files Step 1 intentionally edited (never the whole directory — it holds 68 tracked files incl. regenerable artifacts, and `doc/_design/` mirrors are gitignored):

```bash
git add CLAUDE.md AGENTS.md project/doc/DIPNET_CONVOY_TRIAGE.md project/doc/STPSYR_TRIAGE.md
# plus the specific rule-table doc files edited in Step 1, listed one by one
git commit -m "docs: honest post-wiring test-suite status

The DipNet evaluator and the stpsyr full runner adjudicate through the
full pipeline; status tables carry measured numbers instead of caveats.
test_stpsyr_simple.py, the integration demo and /dip_eval intentionally
stay on the legacy no-graph path. Remaining documented gaps: VIA/GEO-010
(n=<measured>), convoy-paradox fixpoint (Roadmap #1), retreat resolution
(Roadmap #3), coast fidelity in the superfield-only lanes."
```

(memory files are outside the repo — update them, no git add.)

---

## Self-Review (writing-plans checklist)

1. **Spec coverage:** goal = solver-Fehler fixen, Internet-Suites als Benchmark, Geography-Wiring als Voraussetzung. Prereq-Bugfixes: 0, 2 (GEO-004), 3 (void rewrite). Wiring + Scoring: 3 (DipNet), 6+7 (stpsyr). Engine-Konsistenz: 4, 5. Regression-Pinning: 8. Bug-Fixing mit Exit-Kriterium: 9, 10. Reporting: 11. ✓
2. **Placeholder scan:** Tasks 9/10 contain "fix per root cause" by nature (exploratory debugging) — each names suspects, required sub-skill, test-first discipline, and validation gates. No TBDs. ✓
3. **Type consistency:** `Phase`/`TestCase` (Task 6) ↔ Task 7 consumption; `classify_support` new kwargs (Task 2) ↔ service call site; helpers consistently `mko`/`mkr` (E743-safe); `succeeds is None` semantics used everywhere. ✓

## Adversarial Review Log

- **Round 1** (2026-07-07): 6 lenses (correctness, domain, completeness, feasibility, edge-cases, hygiene) + per-finding adversarial verification. 22 CRITICAL/HIGH confirmed, 0 refuted. Major rewrites: new Task 0 (baseline was red); new Task 2 (GEO-004 msup bug — wiring without it collapses the benchmark); Task 3 redesigned (void→hld rewrite identified as root cause of both known FAILs — removed; old Tasks 4/5 "solver bugs" were NOT engine bugs, replaced by Task 8 characterization/pinning); stpsyr lane superfield-only (coast-subfield board contradiction); H-notation handling; case counts corrected (92 parseable, 6.b.14 stub); SYN-009 split strike/correct; commit hygiene (scoped `git add` everywhere, no `-A`); gates extended to the full pytest suite; E743-safe helper names; confidentiality wording.
- **Round 2** (2026-07-08): same harness against Revision 2. 5 CRITICAL/HIGH confirmed, 3 downgraded, 0 refuted. Fixes: Task 0 extended (`ruff format --check` fails on 36 files, masked behind the F401 — mechanical reformat commit + AGENTS.md/CLAUDE.md tracked; line numbers in later tasks marked pre-reformat); Task 3 redesigned again on the strength of a reviewer's instrumented dry run (measured PASS 1517 < gate 1545: 24 regressions from mismatch-class void supports → selective `void ∩ mismatch` rewrite computed from raw DipNet strings; 7 regressions from B.4.2.9 hld-demotion vs DipNet `succeeds=False` → failed-move comparison mapping); Task 7 gained naive retreat-phase handling (datc-6.f.7 contains a retreat block — prior "verified none" claim was wrong); Task 4 red-test scenario corrected (Nap→Apu flanked by ION); SYN-005/SYN-009 interaction fixed; assorted MEDIUM/LOW folded (mypy locations, test_data_pipeline pre-existing ruff errors, 6.a.5 spot-check removed, import placement, scoped fixture staging, citation and count corrections).
- **Round 3** (2026-07-08): against Revision 3. **1 HIGH confirmed** (0 refuted): the Task 3 gate clause "every remaining FAIL is convoy-related" was unsatisfiable — the verifier's independent emulation of the full Task 2+3 design measured **1561 PASS / 41 FAIL / 0 / 0** (better than predicted), with 3 non-convoy FAILs from the live own-unit-attack void-support family that no plan-conformant implementation removes. Fixed: gate re-worded (PASS ≥ 1545, named cases gone; ALL 41 FAILs → Task 9), design-decision 5 carries the measured end state, Task 9 names the 3 cases as bucket-A candidates (suspected DATC-6.D self-dislodgement engine bugs). MEDIUM/LOW folded: red/green split corrected (mismatch test green pre-change), mismatch-index convention + KeyError guard pinned, `run_dipnet_tests.py` staged, worktree ordering constraint on Task 0 Step 4, exit-code caveat in Task 11, count/wording fixes.
- **Round 4** (2026-07-08): against Revision 4. **ZERO CRITICAL/HIGH confirmed — stop rule met. Plan cleared for execution. ✅** MEDIUM/LOW folded anyway: Task 2 names its one deterministic test casualty (`test_full_round_b429_invalid_mve_not_hold_supportable`: supporter `Sil msup Boh` cannot reach Vie under correct GEO-004 → repair test with `Gal msup Boh`); Task-order Task-5→7 dependency wording; Task 11 scoped staging (no directory-add over `project/doc/`) and runner-scoped claim; Task 3c F841 boundary (`void_indices_set`); doc greps exclude gitignored `doc/_design/` mirrors; stale INCONCLUSIVE wording sweep (mappings docstring, `--verbose` help); Task 9 wide sample runs `--workers 8`; "all three FAIL" in Task 5 Step 2; commit-template count fix.
