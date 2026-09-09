# Conflicter Correctness — Subfields, Convoys, Paradoxes, Pattfields

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the conflict resolver correct per the Gilgamesch spec (the original DIP_WORK semantics): subfields fully resolved before the engine (invariant enforced by tests), convoys adjudicated end-to-end (explicit VIA flag, B.3.2.15 convoy-cut immunity, footnote-6 ambiguity fallback), pattfields derived from genuine standoffs (C.2.2/C.2.3.1/C.3.1.3.2), and the remaining documented engine bugs removed.

**Architecture:** Geography (`geography_phase`) normalizes subfields to superfields and classifies orders (`OrderGeoInfo`); the conflict engine (k1–k4) stays field-name agnostic and superfield-only. k1 becomes a three-pass convoy evaluation (optimistic / pessimistic / final) implementing Gilgamesch B.3.2.15 cut immunity and footnote-6 ambiguity detection — bounded, deterministic, no unbounded fixpoint. Patt marking moves into the resolution phases (`t_field.patt`), and `writer` collects marked fields, replacing the heuristic set formula and the `pattfields_include_failed_dests` switch.

**Tech Stack:** Python 3.11+, pydantic v2, pytest. Validation via `make check`, `make examples-check`, `make test-dipnet-quick`, `make test-dipnet-full`, stpsyr suite.

**Semantics sources (authoritative, in order):** Gilgamesch spec (`Gilgamesch/Gilgamesch_1910.pdf`, gitignored — B.3.2.13/14/15 + fn6, B.4.2.9/10, C.2.1–C.2.4, C.3.1.3.2) → original Pascal DIP_WORK behavior → DATC v3.2 (`testdata/datc-v3/DATC_v3_2.html`) as cross-reference only. Where DATC and Gilgamesch diverge (notably the Szykman rule for paradoxes and the "bounced destinations are pattfields" interpretation), **Gilgamesch wins**.

**Out of scope (explicitly):** retreat-phase conflict resolution (DATC 6.H.10–16), winter adjustment/build-disband, DipNet UI, API surface changes beyond the `via_convoy` field.

---

## Verified current state (2026-09-09, do not re-derive)

- Subfield normalization exists and works: `geography/service.py:56-71` collapses `SpN→Spa` etc. via `geography/coast.py:normalize_to_superfield` / `resolve_coast`; `OrderGeoInfo.resolved_coast` carries the coast out-of-band. `eval_model.py:41` documents the invariant. **Missing: enforcement tests** (Task 1) and the B.4.2.9-with-convoy pin (Task 2).
- `Order` has no `via_convoy` field (`model.py:42-52`); `mappings.py:234-237` drops DipNet's ` VIA` suffix. All 137 remaining DipNet 1000-game FAILs involve a VIA order (see AGENTS.md Roadmap #5, GEO-010).
- k1 (`eval/eval_k1.py`) is one-shot: mark → cut (`relevant_moves={nmove}` only — cmove cuts of category-1 supports happen later in k4, unconditionally, without B.3.2.15) → resolve at convoyer fields → dislodge → restrict graph → check routes. Paradox behavior wrong (see Task 8 analysis).
- cmove conversion: `conflict_game.parser:124-137` honors `ConvoyGraph.cmove_candidates` when a graph is supplied (legacy con-scan otherwise). The AGENTS.md "cmove dual source of truth" gap is already closed in code; only the B.4.2.9+convoy interaction test is missing (Task 2).
- `writer` pattfields heuristic (`conflict_game.py:197-214`) + `Switches.pattfields_include_failed_dests`. DATC_ANALYSIS.md documents the 6.D.3/6.F.1-vs-`test_conflict_game_02` conflict. Switch referenced in: `model.py`, `conflict_game.py`, `tests/test_conflict_datc.py`, `doc/_design/status.md`, `doc/DATC_ANALYSIS.md`, `doc/TEST_EXPANSION.md`.
- `test_6_a_1` is assert-only (`test_conflict_datc.py`, calls `conflict_game` without geography — the engine alone cannot reject illegal moves; geography can).
- Convoy-swap head-to-head (Gilgamesch B.3.2.13/C.2.3: two adjacent units swap when at least one moves by convoy) is not handled: k3 (`eval/eval_k3.py:40-43`) only marks nmove↔nmove pairs; a cmove↔nmove pair is resolved by k4 as mutual attacks into occupied fields → both bounce. Wrong.
- `eval_k1.convoy_route_valid` (line 54) silently ignores `Switches.convoy_routing_engine` when `world.convoy_graph` is set; graph path emits no `$cnv` event (legacy `_convoy_route_valid_fixed` does).
- Gilgamesch B.3.2.15 (with footnote 6): *"Eine Bewegung per Convoy reduziert nicht die Stärke der Unterstützung einer Einheit im Zielfeld des Convoys für einen Angriff auf eine der convoyenden Einheiten, die für den Convoy notwendig ist."* — a convoyed move does not cut the support of a unit **at the convoy's destination field** when that support is used **for an attack on a fleet that is necessary for that convoy**. Footnote 6: *"Sollte sich bei der Auswertung eines oder mehrerer Convoys eine Situation geben, die unterschiedliche korrekte Ergebnisse haben könnte (je nachdem, wo man beim Auswerten anfängt) oder die gar paradox ist, bleiben alle beteiligten Einheiten stehen."*
- Gilgamesch C.3.1.3.2: a retreat field must not have had a "Patt von Einheiten" (standoff) in the movement phase. Patt per C.2.2: ≥2 equally-strong strongest attackers ("belagerte Garnison"); per C.2.3.1: head-to-head with equal strengths. **Single-attacker bounces are NOT Patt** (C.2.1). This is the convergent single pattfields rule: it satisfies `test_conflict_game_02` (`set()`), `test_conflict_game_patt_01` (2 attackers on empty `Vie` → `{Vie}`), `test_6_a_11` (2 attackers → `{Tyr}`), and DATC 6.F.1 beleaguered (3 attackers → `{Ber}`). Only the hand-written 6.D.3 expectation `{Tri, Tyr}` (two single-attacker bounces) contradicts it — Gilgamesch wins, that expectation changes to `set()`.

---

## Task 1: Subfield invariant enforcement tests

**Files:**
- Create: `project/tests/test_geo_superfield_invariant.py`

- [ ] **Step 1: Write the invariant tests**

```python
"""Invariant: subfields are resolved before the conflict engine.

Gilgamesch/original-code architecture: the resolver is superfield-only.
Geography (B.4.2 correction phase) collapses SpN/SpS/BuS/BuE/... to their
superfields; the engine never sees a subfield name.
"""
from dipworkpy.geo_model import MapRef
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType


def _subfield_pairs(m) -> list[tuple[str, str]]:
    out = []
    for f in m.field_names():  # protocol method; see geography/map/protocol.py
        for s in m.subfields_of(f):
            out.append((s, f))
    return out


def test_every_subfield_normalizes_to_its_superfield():
    m = MapRef().resolve()  # standard map; or use geography.map.resolve.resolve_map_ref(MapRef())
    for sub, sup in _subfield_pairs(m):
        assert m.superfield_of(sub) == sup, (sub, sup)


def test_geography_output_orders_are_superfield_only():
    m = resolve_map_ref(MapRef())
    req_orders = []
    expected = set()
    for sub, sup in _subfield_pairs(m):
        req_orders.append(Order(nation="Au", utype="A", current=sub, order=None, dest=None))
        expected.add(sup)
    resp = geography_phase(GeographyRequest(orders=req_orders, map=MapRef()))
    for o in resp.orders:
        assert o.current not in {s for s, _ in _subfield_pairs(m)}
        if o.dest:
            assert o.dest not in {s for s, _ in _subfield_pairs(m)}


def test_round_full_moves_and_conflicts_on_superfields():
    """End-to-end: F on SpN holding, A attacking Spa -- conflict runs on 'Spa'."""
    from dipworkpy.round.orchestrator import round_full, RoundRequest
    req = RoundRequest(
        orders=[
            Order(nation="En", utype="F", current="SpN", order="hld", dest=None),
            Order(nation="Fr", utype="A", current="Gas", order="mve", dest="Spa"),
        ],
        unit_positions={"SpN": ("En", "F"), "Gas": ("Fr", "A")},
    )
    res = round_full(req)
    assert res.conflict.resolution is not None
    currents = {o.current for o in res.conflict.resolution.orders}
    assert "SpN" not in currents and "Spa" in currents
```

Note: adjust imports/helpers to the actual `MapProtocol` API (`field_names` may be spelled differently — check `geography/map/protocol.py` first and use what exists; add a `field_names()` protocol method only if missing).

- [ ] **Step 2: Run tests**

Run: `cd project && uv run python -m pytest tests/test_geo_superfield_invariant.py -v`
Expected: PASS (the normalization exists). If `test_geography_output_orders_are_superfield_only` FAILS, that is a real leak — fix `geography/service.py`, do not relax the test.

- [ ] **Step 3: Commit**

```bash
git add tests/test_geo_superfield_invariant.py
git commit -m "test(geo): enforce superfield invariant end-to-end"
```

---

## Task 2: Pin B.4.2.9 + convoy interaction (cmove override semantics)

**Files:**
- Test: `project/tests/test_conflict_geo_info.py` (append)

- [ ] **Step 1: Write the pinning tests**

```python
def test_b429_invalid_move_with_matching_con_orders_becomes_cmove():
    """B.4.2.9 vs GEO-009: a geo-invalid mve WITH ordered convoyers is a valid
    cmove (geography overrides the direct-edge failure). service.py:78-85."""
    orders = [
        Order(nation="En", utype="A", current="Lon", order="mve", dest="Bre"),
        Order(nation="En", utype="F", current="ENG", order="con", dest="Lon"),
    ]
    resp = geography_phase(GeographyRequest(orders=orders, map=MapRef()))
    assert resp.order_geo_info[0].is_valid is True
    assert resp.order_geo_info[0].is_convoy_move is True
    assert resp.order_geo_info[0].effective_behavior == "moves"


def test_b429_invalid_move_without_con_orders_is_umove():
    """B.4.2.9: geo-invalid mve without convoy -> 'holds_no_support' (umove, def 0)."""
    orders = [Order(nation="En", utype="F", current="NTH", order="mve", dest="Pic")]
    resp = geography_phase(GeographyRequest(orders=orders, map=MapRef()))
    info = resp.order_geo_info[0]
    assert info.is_valid is False
    assert info.effective_behavior == "holds_no_support"
```

- [ ] **Step 2: Run**

Run: `uv run python -m pytest tests/test_conflict_geo_info.py -v` — Expected: PASS (documents chosen semantics; closes the AGENTS.md gap "B.4.2.9 invalid-move + convoy interaction undefined").

- [ ] **Step 3: Commit** — `git commit -am "test(geo): pin B.4.2.9 invalid-move + convoy semantics"`

---

## Task 3: `Order.via_convoy` wire field + DipNet `VIA` mapping (GEO-010)

**Files:**
- Modify: `project/dipworkpy/model.py` (class `Order`, lines 42-52)
- Modify: `project/test_data_pipeline/mappings.py:234-237`
- Test: `project/test_data_pipeline/tests/test_mappings_via.py` (create)

- [ ] **Step 1: Add the field to `Order`** (`model.py`):

```python
class Order(BaseModel):
    nation: str
    utype: str = "A"
    current: str  # current field name
    order: Optional[OrderType] = None  # mve, hld, con, hsup. msup
    dest: Optional[str] = None  # target field of mve, con, hsup, msup; may be None if hld.
    via_convoy: bool = False  # GEO-010 / Gilgamesch B.3.2.14: explicit "mve [Convoy]"

    def __log__(self):
        o = self.order if self.order else ""
        d = self.dest if self.dest else ""
        via = " [Convoy]" if self.via_convoy else ""
        return f"{self.nation} {self.utype} {self.current} {o} {d}{via}"
```

- [ ] **Step 2: Parse `VIA` in `mappings.py`** (replace lines 234-237):

```python
    if parts[2] == "-":
        # Move: "A VIE - BUD" or "A VIE - BUD VIA"
        dest = convert_territory(parts[3])
        via_convoy = len(parts) > 4 and parts[-1] == "VIA"
        return Order(
            nation=nation_dwp, utype=utype, current=current,
            order=OrderType.mve, dest=dest, via_convoy=via_convoy,
        )
```

- [ ] **Step 3: Failing tests first (write before Step 1-2 if you want strict TDD; both orders acceptable)**

`project/test_data_pipeline/tests/test_mappings_via.py`:

```python
from dipworkpy.model import Order, OrderType
from test_data_pipeline.mappings import parse_dipnet_order


def test_plain_move_has_no_via():
    o = parse_dipnet_order("A VIE - BUD", "Au")
    assert o.via_convoy is False


def test_via_move_sets_flag():
    o = parse_dipnet_order("A VIE - BUD VIA", "Au")
    assert o.via_convoy is True
    assert o.order == OrderType.mve and o.dest == "Bud"


def test_via_with_coast_suffix():
    o = parse_dipnet_order("F STP/NC - BAR VIA", "Ru")
    assert o.via_convoy is True
```

- [ ] **Step 4: Run + commit**

Run: `uv run python -m pytest test_data_pipeline/tests/test_mappings_via.py -v` — Expected: PASS.
`git add ... && git commit -m "feat(model): Order.via_convoy (GEO-010) + DipNet VIA mapping"`

---

## Task 4: Geography + parser honor `via_convoy` (B.3.2.14)

Semantics (Gilgamesch B.3.2.14): `mve [Convoy]` to an adjacent field where the convoy fails → unit stands, **no effect on the neighbor field** (no support cut), keeps defensive strength (it is a *failed move*, B.4.2.10 does not apply — the order was valid). `mve [Convoy]` with a functioning convoy → moves by convoy even though land route exists. Plain `mve` (no flag) to an adjacent field → moves directly, convoy routes ignored.

Engine mechanics: a flagged move always enters the engine as `cmove`; k1's route check (`my_convoyers` empty or route invalid → `$criv` → `t_order.none`) then yields exactly B.3.2.14 — stands with full defensive strength, attacks nothing, cuts nothing.

**Files:**
- Modify: `project/dipworkpy/geography/service.py:76-85`
- Modify: `project/dipworkpy/conflict_game.py:119-137` (parser cmove conversion)
- Test: `project/tests/test_conflict_datc.py` (append)

- [ ] **Step 1: Geography — flagged moves are convoy moves regardless of candidates** (`service.py`, replace the `if i in cmove_idx:` block at 78-85):

```python
            if i in cmove_idx or o.via_convoy:
                # Explicit convoy intent (GEO-010, B.3.2.14) or ordered
                # convoyers (GEO-009): the move is a convoy move even when the
                # direct land edge fails. If no route survives, k1's route
                # check turns it into a failed move (stands, no effect).
                info.is_valid = True
                info.invalidity_code = None
                info.invalidity_reason = None
                info.effective_behavior = "moves"
                info.is_convoy_move = True
```

- [ ] **Step 2: Parser — cmove conversion for flagged orders even without a graph** (`conflict_game.py:119-137`, replace both branches):

```python
    # change nmoves to cmoves.
    # Single source of truth: geography's GEO-009 classification
    # (convoy_graph.cmove_candidates) plus the explicit GEO-010 flag
    # (Order.via_convoy). Without a graph (legacy callers), the raw
    # con-order scan remains as fallback for unflagged orders.
    cmove_idx: Set[int] = set(convoy_graph.cmove_candidates) if convoy_graph is not None else set()
    for i, o in enumerate(situation.orders):
        if i in cmove_idx or o.via_convoy:
            cmove_field = world.get_field(o.current)
            if cmove_field and cmove_field.order in {t_order.nmove}:
                log.debug("- changing nmove to cmove for field:%s (candidates/via_convoy)", cmove_field)
                cmove_field.order = t_order.cmove
                cmove_field.add_event("$cmove")
    if convoy_graph is None:
        for convoy_field, dest_field in world.get_fields_dests(lambda f: f.order in {t_order.convoy}):
            if dest_field.order in {t_order.nmove}:
                log.debug("- changing nmove to cmove for field:%s because of dest:%s", dest_field, convoy_field)
                dest_field.order = t_order.cmove
                dest_field.add_event("$cmove")
```

(Add `Set` to the `typing` import line at `conflict_game.py:2`.)

- [ ] **Step 3: DATC-style tests** (append to `tests/test_conflict_datc.py`):

```python
def test_b3214_via_convoy_failed_convoy_stands_without_effect():
    """B.3.2.14: mve [Convoy] to ADJACENT field, convoy fails -> unit stands,
    no support cut at the target. (Maps DATC 'Dad's Army' topology minus the
    attack: here the flagged army attacks the supporter of an attack on its
    own convoyer.)"""
    situation = Situation(
        orders=[
            mk_order("En F NTH mve ENG"),        # flagged move via own convoyer? no: see below
        ],
    )
    # concrete case below
    situation = Situation(
        orders=[
            Order(nation="Fr", utype="A", current="Bre", order="mve", dest="Gas", via_convoy=True),
            Order(nation="Fr", utype="F", current="MAO", order="con", dest="Bre"),
            Order(nation="En", utype="F", current="ENG", order="msup", dest="MAO"),  # support attack on MAO
            Order(nation="En", utype="F", current="IRI", order="mve", dest="MAO"),
        ],
    )
    result = conflict_game(situation)  # legacy path: no graph -> fallback scan
    # MAO dislodged by IRI (2 v 1): convoy dead -> Bre stands per B.3.2.14,
    # and Bre's would-be cut of the ENG support never happens (Bre is 'none').
```

Careful when writing the real test: pick a topology where the flagged army's target hosts a support whose cut-status the assertion can check, and assert `succeeds`/`order` fields explicitly (use `mk_oresult(...)` comparisons like the existing tests). Keep the first draft above only as topology inspiration — the committed test must assert concrete `OrderResult`s. Same for the companion test:

```python
def test_b3214_via_convoy_adjacent_direct_move_ignored():
    """B.3.2.14 second sentence: unflagged mve to adjacent field moves directly,
    existing convoy routes ignored (the move is NOT a cmove)."""
```

- [ ] **Step 4: Run the full conflict + geography suites**

Run: `uv run python -m pytest tests/test_conflict_datc.py tests/test_conflict_game.py tests/test_conflict_convoy_graph.py tests/test_geo_convoy.py -q`
Expected: all PASS (watch for regressions in tests that relied on `mve`+`con` to adjacent fields NOT becoming cmoves — none should exist; if one does, re-read the case against B.3.2.14 before touching code).

- [ ] **Step 5: Commit** — `git commit -am "feat(convoy): via_convoy end-to-end per Gilgamesch B.3.2.14 (GEO-010)"`

---

## Task 4b: GEO-009 adjacency exclusion — unflagged adjacent moves are land moves (B.3.2.14 sentence 3)

Discovered during Task 4's reviews (2026-09-09): a stray `con` order demotes an **unflagged** army move to a directly-adjacent field into a `cmove` on the graph path (`GEO-009 classify_cmove_candidates` includes adjacent moves). If that convoy is disrupted, the plain move wrongly stands instead of moving directly — violating Gilgamesch B.3.2.14 sentence 2/3 ("mve ohne Zusatz zieht direkt dorthin, etwaige vorhandene Convoy-Routen werden ignoriert"; DATC agrees). The legacy graph-less con-scan cannot know adjacency (no map) — accepted legacy limitation, documented.

**Files:**
- Modify: `project/dipworkpy/geography/convoy.py` (`classify_cmove_candidates`, ~lines 85-111)
- Test: `project/tests/test_conflict_datc.py` (append)

- [ ] **Step 1:** In `classify_cmove_candidates`, skip an army move when `o.via_convoy` is False AND the army can reach `o.dest` directly by land (`can_reach_by_unit` from `geography/rules.py`) — such moves are land moves even when con orders target them. Non-adjacent unflagged moves keep today's behavior (convoy move by necessity).
- [ ] **Step 2:** Test: unflagged Pic→Bel (adjacent) + F ENG con Pic, convoy fleet dislodged → the army STILL moves directly (succeeds). Counter-test: via_convoy=True same setup → stands (B.3.2.14 sentence 1, covered by Task 4).
- [ ] **Step 3:** Full suite green; the stale GEO-010 comments (`geo_model.py:177-181`, `doc/PHASES.md:44`, `doc/convoy_examples.md:147-149` — flagged stale by Task 4's quality review) are updated in the same commit: GEO-010 is implemented since Task 3/4.
- [ ] **Step 4:** Commit `fix(geo): GEO-009 excludes unflagged adjacent moves (B.3.2.14 sentence 3)`.

---

## Task 5: Convoy swap head-to-head (Gilgamesch B.3.2.13 / C.2.3)

**Files:**
- Modify: `project/dipworkpy/eval/eval_k3.py:38-51`
- Test: `project/tests/test_conflict_datc.py` (append)

- [ ] **Step 1: Extend k3 marking** — head-to-head pairs where **at least one** is a `cmove` swap without conflict (C.2.3: units moving by convoy may exchange fields). Replace the `{mark k3 fields}` block:

```python
    # {mark k3 fields}
    ifield: t_field
    dest_field: t_field
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in {nmove, cmove}):
        if dest_field.order in {nmove, cmove} and dest_field.dest == ifield.name:
            if cmove in (ifield.order, dest_field.order):
                # C.2.3 / B.3.2.13: swap via convoy -- no border conflict.
                # Route validity was already decided in k1 (a failed cmove is
                # 'none' by now), so a surviving cmove here is executable.
                ifield.succeeds = True
                dest_field.succeeds = True
                ifield.add_event("$swap")
                dest_field.add_event("$swap")
                log.debug("k3. convoy swap of fields:%s and:%s", ifield.name, dest_field.name)
            else:
                ifield.fcategory = 3
                dest_field.fcategory = 3
                ifield.add_event("$k3f")
                dest_field.add_event("$k3f")
                log.debug("k3. conflict at border identified of fields:%s and:%s", ifield, dest_field)
```

Verify the downstream marking loop (line 47-50) still uses `fcategory == 3` — swapped fields are not marked, so k3's resolve loop skips them ✓, and k4's `dest_field.order == umove` re-resolve does not trigger ✓. Confirm in k4 that a third attacker on a vacated swap field resolves normally (it does — fcategory==0 path).

- [ ] **Step 2: Test (DATC swap-by-convoy shape, Pic⇄Bel via ENG)**:

```python
def test_b3213_convoy_swap_of_adjacent_units():
    """B.3.2.13: adjacent units exchange fields when at least one has the
    explicit convoy flag and a third unit convoy executes."""
    situation = Situation(
        orders=[
            Order(nation="Fr", utype="A", current="Pic", order="mve", dest="Bel", via_convoy=True),
            Order(nation="Ge", utype="A", current="Bel", order="mve", dest="Pic"),
            Order(nation="En", utype="F", current="ENG", order="con", dest="Pic"),
        ],
    )
    result = conflict_game(situation)
    orders = {(o.nation, o.current): o for o in result.orders}
    assert orders[("Fr", "Pic")].succeeds is None  # moved
    assert orders[("Ge", "Bel")].succeeds is None  # moved
```

And the negative: same orders **without** the flag → both bounce (plain adjacent head-to-head, k3 conflict; note k3's nmove↔nmove path must still resolve it).

- [ ] **Step 3: Run** — `uv run python -m pytest tests/test_conflict_datc.py tests/test_conflict_chain_characterization.py -q` — Expected: PASS (characterization suite is the safety net for k3/k4 changes).

- [ ] **Step 4: Commit** — `git commit -am "feat(k3): convoy swap of adjacent units (B.3.2.13/C.2.3)"`

---

## Task 6: Writer reports convoy-order outcomes (DipNet bucket C)

Rule: a `con` order's `succeeds` is `False` when the convoy did not execute — the convoyed army's move is not a surviving `cmove` (bounced, route disrupted, or the con order itself was geo-invalid). Otherwise `None` (default success). Matches DipNet's `"no convoy"` → `(False, None)` mapping (`mappings.py:275`).

**Files:**
- Modify: `project/dipworkpy/conflict_game.py` (`writer`, moves loop ~182-196)
- Test: `project/tests/test_conflict_game_writer.py` (append)

- [ ] **Step 1: In `writer`, after building `orr`, add**:

```python
        # Bucket C: convoy orders report failure when the convoy did not
        # execute (army did not move via this convoy, or the con order was
        # geo-invalid and collapsed to a hold).
        if f.original_order and f.original_order.order == model.OrderType.con:
            army = world.get_field(f.xref)
            executed = army is not None and army.order == t_order.cmove and army.succeeds
            orr.succeeds = None if (executed and f.order == t_order.convoy) else False
```

(If the con order was geo-invalid it became `t_order.none`; the condition above still reports `False` because `f.order != t_order.convoy`. Plain `f.order == convoy` with executed army → `None`.)

- [ ] **Step 2: Tests**: convoy executes → `succeeds=None`; convoy fleet dislodged (army `none`) → `succeeds=False`; con order without companion mve (GEO-006, via `round_full`) → `succeeds=False`.

- [ ] **Step 3: Run + commit** — `uv run python -m pytest tests/test_conflict_game_writer.py tests/test_conflict_game_convoy_source.py -q` then `git commit -am "feat(writer): report con-order failure when convoy did not execute"`

---

## Task 7: DipNet 100-game validation checkpoint (VIA)

**Files:**
- Modify: `project/doc/DIPNET_CONVOY_TRIAGE.md` (numbers)

- [ ] **Step 1: Run** `make test-dipnet-quick` (100 games).
- [ ] **Step 2: Record** PASS/FAIL/INCONCLUSIVE and confirm the VIA-family FAILs collapsed (baseline: 1595 PASS / 7 FAIL on 100 games pre-VIA; the VIA family was measured on the 1000-game sample: 137 FAILs, all VIA). Any remaining FAIL: triage into the bucket table before proceeding. **Triage taxonomy (user-confirmed 2026-09-09): the external corpora (DipNet dataset, stpsyr suite) are the *comparison baseline* for conflicter correctness — they come from other sites' adjudicators. Each FAIL must be classified as (a) genuine engine bug → fix, (b) rule-interpretation divergence Gilgamesch-vs-DipNet → expected, document (convoy cut immunity B.3.2.15 ≈ 1982 rule vs. DipNet's likely Szykman/2000-style; 6.F.17/6.F.21-family orders; swap; pattfields), or (c) dataset/mapping artifact. Class (b) findings go into the bucket table with the Gilgamesch citation and the DipNet-expected outcome — they are evidence, not regressions.**
- [ ] **Step 3: If FAILs regressed** (class (a) only — new engine bugs introduced by this plan's changes), fix before continuing — do not proceed to Task 8 on a red sample.
- [ ] **Step 4: Commit** — `git commit -am "docs: DipNet triage numbers after GEO-010/VIA"`

---

## Task 8: Convoy paradox resolution — B.3.2.15 cut immunity + fn6 ambiguity (core task)

### Analysis (verified against all DATC 6.F.13–6.F.24 cases)

The paradox family decomposes into two structural rules, NOT an unbounded fixpoint:

**(a) B.3.2.15 cut immunity (resolves 6.F.13–6.F.21):** a convoyed army does not cut the support of a unit located **at its convoy's destination field** when that support is used **for an attack on a fleet that is necessary for the convoy** (necessary = present on every surviving route: `convoy_route_exists(start, dest, graph minus {fleet})` is False). Cases: 6.F.14 (simple paradox), 6.F.16 (Pandin), 6.F.17 (extended), 6.F.18 (betrayal — hold-support of a necessary convoyer also counts: it is "eine Unterstützung ... für einen Angriff auf eine der convoyenden Einheiten" in the defense sense; assert the Gilgamesch outcome, which diverges from DATC's 1982 text where that text implies a 1v1 dislodge), 6.F.19/6.F.20 (multi-route: fleet not necessary → cut allowed), 6.F.21 (Dad's Army — Gilgamesch sides with the 1982 outcome: Clyde's support NOT cut; note this divergence from DATC's preference in the test docstring).

**(b) Footnote-6 ambiguity fallback (resolves 6.F.22–6.F.24):** remaining circular cases are cross-convoy cut dependencies. Detection: evaluate the convoy layer under two extreme cut regimes — **optimistic** (all B.3.2.15-permitted cmove cuts applied) and **pessimistic** (no cmove cuts at all). For each cmove `c`: route survives in both → `c` active; fails in both → inactive; **differs → ambiguous → inactive and its cuts void** (all involved units stand, fn6). Then a **final pass** runs with the decided active set. Verified outcomes: 6.F.22/6.F.23/6.F.24 → both armies stand, supports not cut, non-paradox attacks resolve normally (matches DATC Szykman/1982 outcome). Deterministic, bounded: exactly 3 passes.

**Critical prerequisite:** today the cmove cut of a category-1 support happens in **k4** (`cut_supports(category=4, relevant_moves={cmove, nmove, umove})`), post-hoc and without B.3.2.15. It must move into k1 (the convoy layer), and k4 must respect k1's protection decision durably.

**Files:**
- Modify: `project/dipworkpy/eval/eval_model.py` (add `t_field.patt` here too — Task 10 needs it; add `cut_protected: bool = False`)
- Modify: `project/dipworkpy/eval/eval_k1.py` (restructure into `_k1_pass`)
- Modify: `project/dipworkpy/eval/eval_common.py` (`cut_supports`: skip protected supports)
- Test: `project/tests/test_convoy_paradox.py` (create)

- [ ] **Step 1: `t_field` flags** (`eval_model.py`, bookkeeping fields):

```python
    cut_protected: bool = False  # k1: B.3.2.15-protected support; k4 must not cut it
    patt: bool = False  # movement-phase standoff (C.2.2/C.2.3.1); writer collects
```

- [ ] **Step 2: `cut_supports` respects protection** (`eval_common.py:20`, inside the `if` before decrementing):

```python
        if dest_field.cut_protected:
            field.add_event("$sup_prot")
            continue
```

- [ ] **Step 3: Restructure k1** into a pass function + three-regime driver. Sketch (full body = current `k1_evaluation` logic, adapted):

```python
def _k1_route_survivors(world) -> Dict[str, bool]:
    """{cmove field name: route survives with current dislodgements}."""
    out = {}
    for ifield in world.get_fields(lambda f: f.order in {t_order.cmove}):
        my_convoyers = {
            j.name for j in world.get_fields() if j.order in {t_order.convoy} and j.xref == ifield.name
        }
        out[ifield.name] = convoy_route_valid(world=world, field=ifield, convoyer_names=my_convoyers)
    return out


def _k1_pass(world, regime: str, active: Optional[Set[str]] = None) -> Dict[str, bool]:
    """One k1 evaluation. regime: 'optimistic' | 'pessimistic' | 'final'.
    - optimistic: all cmoves cut (B.3.2.15-filtered)
    - pessimistic: no cmove cuts (cmoves pre-demoted to 'none' after marking)
    - final: only 'active' cmoves cut; others pre-demoted
    Returns route-survival map. Body = current k1_evaluation with:
      * cut_supports(world, 1, {nmove}) as today, then explicit cmove cuts:
        for each cmove c (allowed by regime): dest = get_field(c.dest);
        if dest is hsup/msup with dest.category == 1:
            if _b3215_protected(world, c, dest): dest.cut_protected = True; continue
            # apply cut like cut_supports does (support_strength=0, order=none,
            # succeeds=False, $sup_cut, respecting self_cut_ok)
      * B.3.2.15 helper:
        def _b3215_protected(world, cmove_field, sup_field) -> bool:
            # supported attack target:
            tgt = sup_field.xref if sup_field.order == t_order.hsupport else sup_field.dest
            # necessary convoyer of cmove's own convoy attacked by that support?
            for f in cmove convoyers:
                if f == tgt and not convoy_route_exists(cmove.name, cmove.dest,
                        _restrict_convoy_graph(world.convoy_graph, convoyers - {f})):
                    return True
            return False
    """
```

Driver:

```python
def k1_evaluation(world: t_world):
    if not any(f.order == t_order.convoy for f in world.get_fields()):
        _k1_pass(world, "final", active=set())  # no convoys: plain pass
        return
    snapshot = {k: v.model_copy(deep=True) for k, v in world.fields_.items()}
    routes_opt = _k1_pass(world, "optimistic")
    world.fields_ = {k: v.model_copy(deep=True) for k, v in snapshot.items()}
    routes_pes = _k1_pass(world, "pessimistic")
    world.fields_ = {k: v.model_copy(deep=True) for k, v in snapshot.items()}
    active = {name for name, ok in routes_opt.items()
              if ok and routes_pes.get(name, False)}
    _k1_pass(world, "final", active=active)
```

(`model_copy(deep=True)` on `t_field` with the private `_events` list: verify pydantic copies it per-instance — add a one-off assertion test `_events` is not shared between original and copy; if pydantic does not copy private attrs, switch to `copy.deepcopy` from the stdlib for the snapshot.)

- [ ] **Step 4: k4 cleanup** — no code change expected (pre-demoted cmoves are `none`, protected supports flagged); verify with the characterization suite.

- [ ] **Step 5: Paradox tests** (`tests/test_convoy_paradox.py`) — DATC 6.F.13–6.F.24 translated to DipworkPy field names, each asserting the **Gilgamesch** outcome derived above:

| Case | Expected (Gilgamesch) |
|---|---|
| 6.F.13 unwanted alternative | Lon→Bel succeeds via surviving route; dislodged fleet's route irrelevant |
| 6.F.14 simple paradox | Lon's support NOT cut; Wal→ENG succeeds, ENG dislodged; Bre→Lon fails |
| 6.F.16 Pandin | Lon's support NOT cut; Wal→ENG and Bel→ENG both fail; ENG survives; Bre fails (bounce) |
| 6.F.17 extended | Lon's support NOT cut; ENG survives (2v2 tie); Bre (supported 2v1) dislodges Lon |
| 6.F.18 betrayal | Bel's hsup NOT cut; Nth survives (2v2); Lon→Bel bounces; Skagerrak→Nth bounces |
| 6.F.19 multi-route | Tyr not necessary → Naples' support cut; Rome→Tyr bounces; Ion route alive; Tunis→Naples bounces |
| 6.F.20 unwanted multi-route | Ion not necessary → Naples' support cut; Ion dislodged; Tyr route alive; Tunis→Naples bounces |
| 6.F.21 Dad's Army | Clyde's support NOT cut (Gilgamesch = 1982 outcome; NOTE divergence from DATC's preference); NAO survives 2v2; Liverpool fails |
| 6.F.22 two resolutions | ambiguous → both armies stand, no cuts; Edi→Nth and Pic→ENG succeed (supports intact), ENG/Nth dislodged |
| 6.F.23 exclusive convoys | ambiguous → both stand, no cuts; all four attacks fail (ties); no dislodgements |
| 6.F.24 no resolution | ambiguous → both stand; Edi→Nth succeeds (Lon's msup intact), Nth dislodged; MAO→ENG fails (tie); Bre/Nor fail |

Use the `fixed:` convoy-routing-engine switch or explicit `ConvoyGraph` fixtures as the existing convoy tests do (see `tests/test_convoy_route_valid_fixed.py` / `test_conflict_convoy_graph.py` for conventions).

- [ ] **Step 6: Run everything** — `uv run python -m pytest tests/ -q` (full suite; the characterization suite `test_conflict_chain_characterization.py` guards k2–k4).
Expected: all green. Any characterization failure means the k1 restructure changed non-paradox behavior — fix before proceeding.

- [ ] **Step 7: Commit** — `git commit -am "feat(k1): B.3.2.15 convoy cut immunity + fn6 ambiguity fallback (DATC 6.F.13-24)"`

---

## Task 9: Patt marking — genuine standoffs (C.2.2 / C.2.3.1 / C.3.1.3.2)

**Files:**
- Modify: `project/dipworkpy/eval/eval_common.py` (`resolve_conflict_at_field`)
- Modify: `project/dipworkpy/eval/eval_k3.py` (head-to-head tie)
- Test: `project/tests/test_conflict_patt.py` (create)

- [ ] **Step 1: Mark in `resolve_conflict_at_field`** — count attackers; when the attackers' comparison is a draw **and** ≥2 attackers contested the field, set `ffield.patt = True` (beleaguered garrison, C.2.2; also covers the empty-field multi-attacker tie):

```python
    # inside the attacker loop, count: n_attackers += 1 (initialize before loop)
    # after the loop, next to the existing draw_a handling:
    if draw_a and n_attackers >= 2:
        ffield.patt = True
        ffield.add_event("$patt")
```

- [ ] **Step 2: Mark in k3** — head-to-head equal strengths (C.2.3.1): both fields `patt = True` where the first comparison is a tie (find the tie branch in k3's `resolve_conflict_at_border` usage, lines 55-100 — set both `ifield.patt`/`dest_field.patt` there; `resolve_conflict_at_border` in `eval_common.py:135-139` is the right hook if it can carry the marking, otherwise k3 marks directly).

- [ ] **Step 3: Unit tests** — 1 attacker bounce → not patt; 2 equal attackers on empty field → patt; beleaguered (2 attackers + holder) → patt; head-to-head tie → both patt; head-to-head with a winner → not patt.

Run: `uv run python -m pytest tests/test_conflict_patt.py -q` — Expected: PASS (the `patt` flag from Task 8 Step 1 must exist).

- [ ] **Step 4: Commit** — `git commit -am "feat(eval): mark genuine standoffs (C.2.2/C.2.3.1) on t_field.patt"`

---

## Task 10: Writer consumes `patt` marks; delete the switch

**Files:**
- Modify: `project/dipworkpy/conflict_game.py:197-218` (writer pattfields)
- Modify: `project/dipworkpy/model.py:94-113,116-135` (delete `_ri_pattfields_include_failed_dests` + switch field)
- Modify: `project/tests/test_conflict_datc.py` (6.D.3, 6.F.1, switch-matrix tests)
- Modify: `project/doc/DATC_ANALYSIS.md`, `project/doc/_design/status.md`, `project/doc/TEST_EXPANSION.md` (switch references)

- [ ] **Step 1: Writer** — replace lines 197-214 (formula + switch) with:

```python
    # Pattfields (C.3.1.3.2): fields with a movement-phase standoff
    # (C.2.2 beleaguered / multi-attacker tie, C.2.3.1 head-to-head tie).
    # Single-attacker bounces are NOT patt (C.2.1) and never block retreats
    # beyond being occupied/contested.
    pattfields = {f.name for f in world.get_fields(lambda f: f.patt)}
```

- [ ] **Step 2: Delete the switch** — remove `pattfields_include_failed_dests` from `Switches` and the `_ri_pattfields_include_failed_dests` docstring constant.

- [ ] **Step 3: Update tests**:
  - `test_6_d_3`: remove the switch; expectation becomes `pattfields=set()` with a comment: single-attacker bounces are not standoffs per Gilgamesch C.2.1; the old `{Tri, Tyr}` was the DATC-strict bounced-destinations convention.
  - `test_6_f_1`: remove the switch; `pattfields={"Ber"}` stays (genuine beleaguered standoff).
  - Delete `test_6_d_3_pattfields_switch` and `test_6_f_1_pattfields_switch`.
  - Grep the whole repo for `pattfields_include_failed_dests` and update every doc hit (`doc/DATC_ANALYSIS.md` gets a closing note: resolved by genuine-Patt rule per Gilgamesch, switch deleted).

- [ ] **Step 4: Full suite** — `uv run python -m pytest tests/ -q`.
Audit every remaining `pattfields=` expectation in `tests/test_conflict_game*.py` against the genuine-Patt rule: `test_conflict_game_02` `set()` ✓, `patt_01` `{Vie}` (2 attackers) ✓, `test_6_a_11` `{Tyr}` (2 attackers) ✓. Any expectation that encodes single-bounce destinations must change to `set()` — per Gilgamesch, not per the old formula.

- [ ] **Step 5: Commit** — `git commit -am "feat(writer): pattfields = genuine standoffs per C.3.1.3.2; delete pattfields_include_failed_dests"`

---

## Task 11: $cnv event for graph path + routing-engine override warning

**Files:**
- Modify: `project/dipworkpy/eval/eval_k1.py:52-66`

- [ ] **Step 1: In `convoy_route_valid`, graph branch** — emit the same debug event family the fixed engine uses:

```python
    if world.convoy_graph is not None:
        graph = _restrict_convoy_graph(world.convoy_graph, convoyer_names)
        ok = convoy_route_exists(field.name, field.dest, graph)
        field.add_event(f"$cnv:{'graph' if ok else 'none'}")
        if world.switches.convoy_routing_engine:
            _logger.warning(
                "convoy_graph is set; ignoring Switches.convoy_routing_engine=%r",
                world.switches.convoy_routing_engine,
            )
        return ok
```

- [ ] **Step 2: Test** — extend `tests/test_conflict_convoy_graph.py`: graph-mode resolution includes a `$cnv` event on the cmove field; switch set + graph set logs a warning (`caplog`).
- [ ] **Step 3: Run + commit** — `uv run python -m pytest tests/test_conflict_convoy_graph.py -q` then `git commit -am "feat(k1): $cnv event + warning on graph/engine override"`

---

## Task 12: Tighten `test_6_a_1` (illegal move rejected via geography)

**Files:**
- Modify: `project/tests/test_conflict_datc.py` (`test_6_a_1`)

- [ ] **Step 1: Rewrite via the geography-aware path** (engine-only calls cannot reject illegal moves by design — the engine is field-name agnostic):

```python
def test_6_a_1():
    """6.A.1 via round_full: an illegal non-adjacent move is rejected by
    geography (B.4.2.9 -> holds_no_support) and reported as a failed order."""
    req = RoundRequest(
        orders=[Order(nation="En", utype="F", current="NTH", order="mve", dest="Pic")],
        unit_positions={"NTH": ("En", "F")},
    )
    res = round_full(req)
    o = res.conflict.resolution.orders[0]
    assert o.order == OrderType.hld      # move collapsed to hold
    assert o.succeeds is False           # and it did not succeed
```

- [ ] **Step 2: If `succeeds is False` fails** (geo-invalid umove currently keeps `succeeds=True` default → writer reports `None`): that is a real bug — in `conflict_game.t_field_from_order` (`holds_no_support` branch, line 42-49) add `field.succeeds = False` via the t_field constructor kwargs, and check the whole suite for expectations that an invalid move reports success (there must be none that defensibly wants that).
- [ ] **Step 3: Run + commit** — `uv run python -m pytest tests/ -q` then `git commit -am "test(datc): 6.A.1 rejects illegal move via geography; B.4.2.9 umove reports failure"`

---

## Task 13: Document `rule_interpretation_IX_3` / `IX_7` DATC mapping + switch tests

**Files:**
- Modify: `project/dipworkpy/model.py` (`_ri_9_3` docstring + `IX_7`)
- Create: `project/tests/test_rule_interpretations.py`

- [ ] **Step 1: Map to DATC v3.2**: `rule_interpretation_IX_3` (values 0/1/2, the "self-dislodgement via support of the defender's nation" family) corresponds to **DATC 6.D.10–6.D.12** ("move with support of the unit in the destination field" family — verify the exact case numbers in `testdata/datc-v3/DATC_v3_2.html` section 6.D before writing). Document the mapping in the `_ri_9_3` docstring constant, including a one-line statement per value. Do the same for `IX_7` (k3 head-to-head strength comparison variant, C.2.3.1) — DATC 6.C.* head-to-head family.
- [ ] **Step 2: Tests across switch positions** — one DATC 6.D.10-style scenario run under each value of `rule_interpretation_IX_3` (0/1/2), asserting the differing outcomes from the Gilgamesch example in `_ri_9_3` (Au F MID-ENG / Bre S MID / Pic-Bre topology); same pattern for `IX_7` with a head-to-head pair.
- [ ] **Step 3: Run + commit** — `uv run python -m pytest tests/test_rule_interpretations.py -q` then `git commit -am "test/docs: IX_3/IX_7 DATC mapping + switch-position tests"`

---

## Task 14: Full validation + documentation refresh

**Files:**
- Modify: `project/doc/DIPNET_CONVOY_TRIAGE.md`, `project/doc/DATC_ANALYSIS.md`, `AGENTS.md`, `CLAUDE.md` (status tables), `project/doc/GEOGRAPHY.md` (via_convoy + patt semantics)

- [ ] **Step 1: `make check`** — Expected: fully green.
- [ ] **Step 2: `make examples-check`** — Expected: green.
- [ ] **Step 3: `make test-dipnet-quick`** (100 games) — record; compare against the 1595/7 baseline.
- [ ] **Step 4: `make test-dipnet-full`** (1000-game sample, 8 workers) — record; the 137 VIA FAILs must be gone; triage any new FAIL family before closing, using the class (a) bug / (b) Gilgamesch-vs-DipNet interpretation divergence / (c) dataset artifact taxonomy from Task 7 Step 2. The stpsyr suite (Step 5) gets the same treatment. Class (b) divergences are documented evidence of the Gilgamesch rule reading — they close the mission only when each carries a Gilgamesch citation (spec section) and the DipNet-expected outcome.
- [ ] **Step 5: stpsyr suite** — `uv run python -m pytest tests_from_stpsyr -q`; baseline 77 PASS on `test-stpsyr-full`. Same triage taxonomy for any failure.
- [ ] **Step 6: Update docs**: triage numbers; DATC_ANALYSIS.md closing note (pattfields resolved); GEOGRAPHY.md sections for `via_convoy` (B.3.2.14) and genuine-Patt pattfields (C.3.1.3.2); AGENTS.md: close Roadmap #1/#2 and the Known Gaps lines (convoy paradox fixpoint → implemented as B.3.2.15+fn6; pattfields → resolved; cmove dual source of truth → closed; B.4.2.9+convoy → pinned by test; $cnv → emitted; weak test_6_a_1 → tightened; IX_3/IX_7 → mapped+tested). Mark the honest-DATC section: paradox family 6.F.13–6.F.24 now covered (Gilgamesch semantics, documented divergences: 6.F.17, 6.F.21).
- [ ] **Step 7: Commit** — `git commit -am "docs: close convoy/pattfields roadmap items after correctness pass"`

---

## Self-Review (done at plan time)

1. **Spec coverage:** user goals ↔ tasks — "Bugs entfernt" → Tasks 6, 10-13 (writer bucket C, pattfields, $cnv, 6_a_1, IX_3/IX_7); "Convoys funktionieren" → Tasks 3-5, 7, 8 (VIA, swap, B.3.2.15+fn6, DipNet validation); "Geografie muss existieren" → exists (verified), Tasks 1-2 enforce; "Subfields vorher aufgelöst, Engine agnostisch" → Task 1 enforces the existing invariant. Gap: none.
2. **Placeholders:** Task 4 Step 3 contains a draft test deliberately marked as topology inspiration with an instruction to write concrete assertions — the implementer must commit concrete `mk_oresult` assertions. Task 13 Step 1 requires verifying DATC case numbers in the HTML before documenting (explicit, bounded).
3. **Type consistency:** `t_field.patt`/`cut_protected` introduced in Task 8 Step 1, consumed in Tasks 9/10/11; `Order.via_convoy` introduced Task 3, consumed Tasks 4-5; `_k1_pass`/`_k1_route_survivors`/`_b3215_protected` defined Task 8, used nowhere else.

## Risks / decisions locked at plan time

- **Gilgamesch over DATC** where they conflict (6.F.17, 6.F.21, 6.D.3 pattfields). This matches the user's requirement ("wie der Originalcode") and the project's spec hierarchy. Divergences documented in test docstrings and Task 14 docs.
- **Three-pass convoy evaluation instead of an unbounded fixpoint**: faithful to fn6 ("unterschiedliche korrechte Ergebnisse je nach Start" ⇔ optimistic/pessimistic route status differs), verified against all DATC 6.F.13–6.F.24 case analyses above, bounded and deterministic. If a future case shows a within-regime circularity the two extremes cannot see, extend to per-cmove dual evaluation — documented as a known limitation in Task 8's tests.
- **k4 no longer cuts category-1 supports post-hoc for active cmoves** — that responsibility moved into k1 with B.3.2.15 protection. The characterization suite plus full DipNet sample are the guard.
