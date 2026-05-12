# DipworkPy — Comprehensive Design Spec

**Date:** 2026-05-12
**Author:** Brainstormed with Torsten Will (Claude as scribe)
**Status:** Draft for review
**Scope:** Service-oriented re-architecture covering Geography, Syntax, Conflict Resolution, DDL renderer, test strategy, roadmap.

---

## 0. Executive Summary

DipworkPy currently implements a 5-phase conflict resolution algorithm with ~19 % PASS rate on a 100-game DipNet sample and 7/10 DATC tests green. The next development push has three intertwined goals:

1. **Make the Conflict Resolver correct** — fix the three known DATC failures and reduce the ~466 DipNet fails.
2. **Introduce a Geography component** — separate, swappable, FIELDS-spec-based; supplies an adjacency subgraph to the Conflict Resolver for convoy routing while staying cleanly decoupled.
3. **Architect as a set of services**, not a monolith — each phase (Syntax, Geography, Conflict, …) is independently callable via HTTP, with full diagnostics for UI integration. The Pascal-era pipeline shape remains, but each module is now a stateless service.

This spec also covers a DDL (Diplomacy Diagram Language) for living documentation and tests, and a roadmap covering refactor, geography rollout, DATC fixes, DipNet quota improvement, and FastAPI surface.

**Out of scope:** Retreat resolution, supply-center counting, build/disband, multi-variant maps, Gilgamesch-only extras (Erscheinungen, Magie, Furten, fly, Transmitter, …), authentication, async workflows.

---

## 1. Architectural Principles

### 1.1 Services, not modules

Every phase of a Diplomacy round (Syntax, Geography, Conflict Resolution, Retreats, …) is implemented as an independently usable service with:

- Its own request/response DTOs (Pydantic).
- A single pure function `phase(req) → resp` as the canonical entry point — stateless, no IO.
- A thin FastAPI router (`api.py`) for the REST surface.
- A full diagnostic audit trail in the response (each rule check logged, not just corrections).

The Pascal-style pipeline still describes the natural composition order, but it is not the truth — the truth is each service in isolation. A consumer (orchestrator, UI, third-party) may chain them, mix them, or replace them.

### 1.2 Component isolation

- `conflict/` imports nothing from `geography/` or `syntax/` (only shared models from `model.py` and `geo_model.py`).
- `geography/` imports nothing from `eval/`.
- The map is known only to Geography and Syntax — the Conflict Resolver sees a pre-computed `ConvoyGraph`, never the full map.

### 1.3 PBM correction semantics, not "validation"

Following the German Postspiel tradition (Schröpl, Kautzsch, Interzine/Amtsblatt; canonical reference: Gilgamesch-Regeln V1.9.10 by Roland Rölig / Lukas Kautzsch), order processing follows a three-stage cascade per **Gilgamesch B.2.6**:

- **gültig** (valid): formal + geographic preconditions met — Geography phase responsibility.
- **wirksam** (effective): not overridden by magic/phenomenon — out of scope for us (placeholder).
- **durchgesetzt** (enforced): wins its conflict — Conflict Resolver responsibility.

Geography does **not rewrite orders**. It marks them, and the Conflict Resolver consumes the markers. This preserves the critical PBM asymmetry between invalid moves (no hold-support) and invalid supports/convoys (unit holds and is supportable).

### 1.4 Geography as Code

The map is text — versioned, diffable, swappable. The DDL renderer turns the same text into pictures for documentation and into test fixtures for automation. One source of truth, three artifacts.

---

## 2. Service Architecture

### 2.1 Module layout

```
project/dipworkpy/
  model.py                       # Core types: Order, OrderType, Switches, ConflictResolution
  geo_model.py                   # MapRef, MapDefinition, ConvoyGraph, OrderGeoInfo, FieldType, Edge
  diag.py                        # Diagnostic, severity enum

  eval/                          # ← was dip_eval/
    eval_model.py                # t_field, t_world, t_order
    eval_common.py
    eval_k0.py .. eval_k4.py

  syntax/
    model.py                     # SyntaxRequest, SyntaxResponse
    rules.py                     # SYN-001..008 rule implementations
    service.py                   # syntax_phase(req) -> resp
    api.py                       # FastAPI router

  geography/
    model.py                     # GeographyRequest, GeographyResponse
    map/
      protocol.py                # MapProtocol
      standard.py                # StandardMap (loads standard.json)
      inline.py                  # InlineMap adapter for DDL/test maps
      registry.py                # map_id -> MapProtocol
      data/
        standard.json            # the bundled map data file (JSON, regenerable from FIELDS-spec via converter)
    rules.py                     # GEO-001..010 rule implementations
    convoy.py                    # ConvoyGraph extraction
    coast.py                     # Subfield resolution
    service.py                   # geography_phase(req) -> resp
    api.py

  conflict/
    model.py                     # ConflictRequest, ConflictResponse
    parser.py                    # builds t_world from ConflictRequest + order_geo_info
    writer.py                    # builds ConflictResponse from t_world
    service.py                   # conflict_game(req) -> resp  (main entry)
    api.py

  round/
    orchestrator.py              # round(...) chains the phases
    api.py

  tools/
    dwex/                        # Diplomacy Diagram Language
      lang.py                    # parser + AST
      to_situation.py
      to_map.py
      render_png.py
      generate_index.py          # builds EXAMPLES.md
      cli.py

  api_app.py                     # FastAPI app — mounts all routers
```

### 2.2 Data flow

```
        Order[] + unit_positions
                │
                ▼   syntax_phase()
        Order[] (struck + hold-defaults)
                │
                ▼   geography_phase()
        Order[] (superfield-normalized)
        OrderGeoInfo[] (per-order classification)
        ConvoyGraph
                │
                ▼   conflict_game()
        ConflictResolution
                │
                ▼   (future) retreats_phase()
                  ...
```

Each arrow is a pure function. Each artifact between arrows is a serializable DTO. The orchestrator threads them together for convenience; the truth is the individual services.

### 2.3 Map referencing

```python
class MapRef(BaseModel):
    map_id: Optional[str] = "standard"
    inline_map: Optional[MapDefinition] = None
```

`inline_map` (if set) wins; otherwise `map_id` is looked up in `geography/map/registry.py`. Custom maps (variants, test mini-maps) can be passed inline without server-side registration.

### 2.4 Diagnostics

```python
class Diagnostic(BaseModel):
    phase: Literal["syntax", "geography", "conflict", "round"]
    rule: str                    # "GEO-002", "SYN-005", ...
    severity: Literal["info", "warning", "correction", "error"]
    order_index: Optional[int]   # index into the orders list
    message: str
    details: dict[str, Any] = {}
```

Every rule evaluation produces a diagnostic — even no-ops with `severity="info"` — so a consuming UI can show **which rules were checked**, not just which fired.

---

## 3. Geography Service

### 3.1 MapProtocol

The map is modeled after the FIELDS spec — separate passability for army, fleet, and convoy-move, per directed edge, with explicit coast-disambiguation values.

```python
class FieldType(str, Enum):
    LA  = "LA"   # inland land (army only)
    LCB = "LCB"  # coastal land, simple coast
    LCA = "LCA"  # coastal land with split coasts (superfield)
    LC  = "LC"   # coastal land, single coast
    LCF = "LCF" # subfield entry of an LCA
    L   = "L"    # pure inland
    O   = "O"    # ocean / sea
    COL = "COL"  # off-map

class Passable(str, Enum):
    YES = "ja"
    NO  = "nein"
    NA  = "-"     # not applicable on this side
    IMP = "imp"   # impossible: coast required, no default

class Edge(BaseModel):
    army:         Passable | str   # str = required subfield name
    fleet:        Passable | str
    convoy_move:  Passable

class MapProtocol(Protocol):
    map_id: str

    def field_exists(self, fld: str) -> bool: ...
    def field_type(self, fld: str) -> FieldType: ...
    def superfield_of(self, fld: str) -> str: ...
    def subfields_of(self, fld: str) -> list[str]: ...
    def is_supply_center(self, fld: str) -> bool: ...
    def home_center_of(self, fld: str) -> Optional[str]: ...

    def edge(self, frm: str, to: str) -> Optional[Edge]: ...
    def neighbors(self, fld: str) -> set[str]: ...

    def army_passable(self, frm: str, to: str) -> bool: ...
    def fleet_passable(self, frm: str, to: str) -> Passable | str: ...
    def convoy_passable(self, frm: str, to: str) -> bool: ...
```

Implementations:
- `StandardMap` loads from `geography/map/data/standard.json` — the bundled, repo-owned map data file. JSON is chosen because it (a) parses with the Python stdlib, (b) round-trips cleanly through Pydantic, (c) diffs sensibly in code review, and (d) is the same shape as the `MapDefinition` used by `InlineMap`. A small converter (`tools/fields_to_json.py`) can ingest any external FIELDS-spec text format and emit this canonical JSON.
- `InlineMap` is built from a `MapDefinition` passed in the request — used for DDL test fixtures and custom variants.

### 3.2 What Geography does

Geography is a **classifier + normalizer**, not a validator:

1. Classifies each order as `gültig` per Gilgamesch B.2.6.1.
2. Resolves subfields deterministically where the move destination disambiguates the coast.
3. Normalizes orders to superfield form for the Conflict Resolver.
4. Extracts the `ConvoyGraph` from map + convoy orders.
5. Emits a `Diagnostic` for every rule evaluation.

Geography **never rewrites** an order to a hold. Effect on holding/support behavior is carried in `OrderGeoInfo`.

### 3.3 OrderGeoInfo

```python
class OrderGeoInfo(BaseModel):
    order_index: int

    is_valid: bool                          # Gilgamesch B.2.6.1
    invalidity_code: Optional[str] = None
    invalidity_reason: Optional[str] = None

    effective_behavior: Literal[
        "moves",              # valid mve — conflict resolver handles
        "holds_no_support",   # invalid mve (B.4.2.9) — unit stays, NOT hold-supportable
        "holds_supportable",  # invalid hld/sup/con (B.4.2.10) — unit holds, IS hold-supportable
        "holds_explicit",     # explicit hld order
    ]

    resolved_coast: Optional[str] = None    # for fleet on split-coast superfield
    is_convoy_move: bool = False             # cmove classification (parallel mve+con order pair)
```

### 3.4 Rule set

| ID | Source | Rule | Effect |
|----|--------|------|--------|
| GEO-001 | B.2.6.1(3) | `mve` destination doesn't exist on the map | `holds_no_support` |
| GEO-002 | B.2.6.1(2) | `mve` start == destination | `holds_no_support` |
| GEO-003 | B.2.6.1.1(a/b) | `mve` destination neither neighbor nor convoyable | `holds_no_support` |
| GEO-004 | B.3.1.1 + Fn. 4 | `sup`: supporter cannot reach the supported destination from a direct neighbor (no convoy, no furt) | `holds_supportable` |
| GEO-005 | B.3.2.1 | `con`: convoyer not on a sea field | `holds_supportable` |
| GEO-006 | B.3.2.1 | `con`: convoyed move cannot route through this convoyer (pairwise sea-adjacency missing) | `holds_supportable` |
| GEO-007 | FIELDS | Subfield resolution when the move destination uniquely determines the coast | annotate `resolved_coast`, order stays valid |
| GEO-008 | output | Superfield normalization in output | subfield refs in orders → superfield, info preserved in `resolved_coast` |
| GEO-009 | B.3.2 | `mve` with a matching `con` order: classify as cmove for k1 | `is_convoy_move=True` |
| GEO-010 | B.3.2.14 (future) | Explicit `mve [Convoy]` flag passed through to conflict resolver | `explicit_via_convoy=True` *(not implemented in first cut; placeholder)* |

### 3.5 ConvoyGraph

```python
class ConvoyGraph(BaseModel):
    sea_edges: set[tuple[str, str]]        # SEA<->SEA
    coastal_edges: set[tuple[str, str]]    # SEA<->COAST
    convoyer_fields: set[str]              # {f.current : f.order==con}
    cmove_candidates: set[int]             # order indices of cmove-classified
```

The Conflict Resolver runs pathfinding on this graph via `graphs.find_shortest_path` — geography knowledge is **injected as data**, not as a service callback.

### 3.6 PBM research queue

Before tightening GEO-005 / GEO-006 / GEO-004 (in their stricter PBM forms), consult primary sources:

- **R-PBM-1** — Convoy validity edge cases in German PBM rules (Schröpl, Kautzsch). Concrete questions: convoy from land field? convoy with non-adjacent coastal endpoints?
- **R-PBM-2** — Is "geographic support cutting" a real PBM rule, or is GEO-004 already canonical?
- **R-PBM-3** — Conflict resolver behavior when `order_geo_info` reports `unknown_field` — strike entirely, or treat as `holds_no_support`?

Findings land in `project/doc/PBM_RULES.md`. Implementation of GEO-005 / GEO-006 / refined GEO-004 follows the research.

---

## 4. Syntax Service

### 4.1 Role

First phase. Handles purely formal-grammatical correctness. Inputs from a real user contain typos, wrong fields, double orders, missing units, etc.

### 4.2 Rule set

| ID | Rule | Effect |
|----|------|--------|
| SYN-001 | Unknown nation for active game state | strike order |
| SYN-002 | Unknown unit type (only if `strict_unit_types=True`) | strike order |
| SYN-003 | Unknown order type (not in `hld`/`mve`/`hsup`/`msup`/`con`) | strike order |
| SYN-004 | Field name not on map (current, dest, xref) | strike if `current` affected; otherwise pass to Geography (becomes GEO-001) |
| SYN-005 | Multiple orders for the same unit | strike all conflicting orders (B.4.2.9: "mehrfach unterschiedlich befehligt") |
| SYN-006 | Order on a field without a unit per current `unit_positions` | strike order |
| SYN-007 | Unit-type/field-type mismatch (e.g. `A NTH`) — only if `strict_unit_types=True` | strike order |
| SYN-008 | Hold-default injection: for every unit in `unit_positions` without a surviving order, inject `hld` (B.4.1.2 NMR + general PBM "no order received") | append `hld` to orders |

### 4.3 Behavior of struck orders

A struck order disappears from the output. SYN-008 then injects a default `hld` for its unit, so downstream phases always see a complete and consistent set. The PBM principle ("kein Befehl, fehlerhafter Halte/sup/con-Befehl ⇒ unit hält und ist hold-supportable") is realized via this mechanism.

### 4.4 Switches

```python
class Switches(BaseModel):
    # ... existing ...
    strict_unit_types: bool = False    # default off (std-Diplomacy); on for Gilgamesch-style strictness
```

### 4.5 Request / Response

```python
class SyntaxRequest(BaseModel):
    orders: list[Order]
    unit_positions: dict[str, tuple[str, str]]   # field -> (nation, utype)
    map: MapRef = MapRef()
    switches: Switches = Switches()

class SyntaxResponse(BaseModel):
    orders: list[Order]               # surviving + hold-defaults
    diagnostics: list[Diagnostic]
```

---

## 5. Conflict Resolver Correctness

### 5.1 Three failure surfaces

| Surface | Symptom | Strategy |
|---------|---------|----------|
| Known DATC failures (6.D.2, 6.D.3, 6.F.1) | 3 docs-flagged red tests | Per-case spec diff → bug-or-switch decision → fix or switch + test |
| DipNet `–` fails (~466 in 100-game sample) | 29 % of test cases | Cluster reporter → top-N pattern fix → regression test per cluster |
| DipNet `?` inconclusive (~829) | 51 %, of which 632 void + 197 convoy | After Geography lands, re-run; void cases become decidable |

### 5.2 DATC analysis flow

1. Extract the DATC spec text for the failing case.
2. Diff our actual output vs. the DATC expected output, order-for-order.
3. Trace to the algorithm phase (k1 / k2 / k3 / k4 / k0).
4. Decide: **bug** (fix in `eval/eval_k*.py` + new test) or **deliberate variant** (introduce switch, both behaviors preserved).
5. Document in `project/doc/DATC_ANALYSIS.md`, one section per case.

### 5.3 DipNet cluster reporter

Extend `test_data_pipeline/run_dipnet_tests.py` with `--cluster-failures`:

- For each failed test case, derive an order-type signature, e.g. `{nmove:3, hsup:2, msup:1, con:0}`.
- Annotate with the phase where the divergence appears.
- Group by signature, sort descending by count, output top-N clusters with 3 example games each.
- Output to `project/doc/DIPNET_CLUSTERS.md`.

This converts a 466-failure mess into a triaged backlog.

### 5.4 `eval/` refactor

Pure rename, no behavior change:

| From | To |
|------|-----|
| `dipworkpy/dip_eval/` | `dipworkpy/eval/` |
| `from dipworkpy.dip_eval import ...` | `from dipworkpy.eval import ...` |

Existing tests verify zero-drift.

### 5.5 `order_geo_info` integration in the conflict parser

In `conflict/parser.py`:

```python
def t_field_from_order(o: Order, geo: Optional[OrderGeoInfo]) -> t_field:
    if geo is None or geo.effective_behavior == "moves":
        # current behavior
        ...
    elif geo.effective_behavior == "holds_no_support":
        # invalid mve per B.4.2.9: stays put, not hold-supportable
        # set t_order.umove directly in the internal model
        order = t_order.umove
        # but preserve original Order with order=mve for writer
    elif geo.effective_behavior == "holds_supportable":
        # invalid hld/sup/con per B.4.2.10: holds normally, supportable
        order = t_order.none
    elif geo.effective_behavior == "holds_explicit":
        order = t_order.none
```

When `order_geo_info=None`, the parser falls back to current behavior — existing unit tests that call `conflict_game` directly without a Geography pass keep working.

The asymmetry of B.4.2.9 vs B.4.2.10 is realized by the choice of internal state: `t_order.umove` is a failed move (no hold-support reaches it), `t_order.none` is a regular hold (hold-support applies).

### 5.6 Conflict request

```python
class ConflictRequest(BaseModel):
    orders: list[Order]
    order_geo_info: Optional[list[OrderGeoInfo]] = None    # parallel to orders
    convoy_graph: Optional[ConvoyGraph] = None
    switches: Switches = Switches()

class ConflictResponse(BaseModel):
    resolution: ConflictResolution
    diagnostics: list[Diagnostic]
```

---

## 6. DDL — Diplomacy Diagram Language

### 6.1 Goal

One text source per example produces: a PNG (for docs), a `Situation` (for automated tests), an expected `ConflictResolution` (for assertions), and optionally an inline map (for Geography). Living documentation that cannot drift.

### 6.2 Syntax (PlantUML-inspired)

```
@dwex
title: DATC 6.A.7 — Two units bouncing on same field
desc:  Two armies move to the same empty field with equal strength.

map {
  Vie LA 0,0
  Mun LA 2,0
  Tyr L  1,1

  Vie -- Mun
  Vie -- Tyr
  Mun -- Tyr
}

orders {
  Au A Vie mve Tyr !
  Ge A Mun mve Tyr !
}
@end
```

**Map block:**

- Field: `<Name> <Type> <x>,<y>` — Type from FIELDS spec (`LA`, `LCB`, `LCA`, `LC`, `LCF`, `L`, `O`, `COL`).
- Edge undirected default: `A -- B` (army + fleet + convoy passable).
- Edge modifier: `A --A B` (army only), `A --F B` (fleet only), `A --C B` (convoy-only), `A --AF B` (= `--`).
- Subfields: `Spa[N] LC 0,0.3` declares `SpN` as coast variant of `Spa`.
- Coast-required edge: `Mar -- SpS`.

**Orders block:** existing DipworkPy notation, with `!` = failed and `>` = dislodged. Orders without a marker = expected success.

**Optional blocks:**

```
switches { rule_interpretation_IX_3: 1 }
pattfields { Tyr }
note { Explains why this example matters in human terms. }
```

### 6.3 Renderer

`matplotlib` backend, pure-Python. Layout uses explicit `<x>,<y>` field positions. Defaults:

| Element | Style |
|---------|-------|
| Field `LA`/`L` | tan circle |
| Field `LC`/`LCB`/`LCA`/`LCF` | sand circle |
| Field `O` | light-blue circle |
| Edge (army+fleet) | solid gray |
| Edge (army only) | solid green |
| Edge (fleet only) | solid blue |
| Unit `A` | square marker, nation color |
| Unit `F` | triangle marker, nation color |
| `mve` succeeded | solid green arrow |
| `mve` failed (`!`) | dashed red arrow |
| `mve` cmove | green arrow + "C" overlay on convoyer |
| `hsup` | thin blue line, label "S" |
| `msup` | thin blue line + arrowhead, label "S" |
| `con` | wavy line through sea field, label "C" |
| Dislodged (`>`) | red "DISLODGED" badge |
| Pattfield | gray hatching over field |

Nation palette: Au red, En blue, Fr lightblue, Ge dark, It green, Ru white, Tu yellow, Xx gray.

### 6.4 CLI

```
python -m dipworkpy.tools.dwex render <path.dwex>
python -m dipworkpy.tools.dwex render-all <dir>
python -m dipworkpy.tools.dwex validate <path.dwex>
python -m dipworkpy.tools.dwex to-json <path.dwex>
```

Makefile: `make examples` (render-all + validate-all), `make examples-check` (validate only, for CI).

### 6.5 Documentation surface

```
project/doc/examples/
  README.md                  # index + DDL language reference
  dwex/
    01_basic_hold.dwex
    01_basic_hold.png        # committed alongside source
    ...
    datc/
      6A07_two_units_bouncing.dwex
      6A07_two_units_bouncing.png
      ...
project/doc/EXAMPLES.md      # generated from dwex/
```

PNG files are committed so GitHub's Markdown preview renders them inline. A CI job verifies the committed PNGs are up-to-date with their `.dwex` source.

### 6.6 Test integration

```python
@pytest.mark.parametrize("path", sorted(DWEX_DIR.rglob("*.dwex")), ids=lambda p: p.stem)
def test_dwex_example(path):
    doc = parse_file(path)
    situation = to_situation(doc)
    expected  = to_expected(doc)
    result = conflict_game(situation)
    assert result <= expected
```

Every documented example is automatically a regression test.

### 6.7 First tranche

| # | Title | Demonstrates |
|---|-------|--------------|
| 01 | Single Hold | trivial baseline |
| 02 | Single Move | basic arrow |
| 03 | Equal Bounce | two armies, same dest |
| 04 | Support Hold | hsup visualization |
| 05 | Support Move | msup chain |
| 06 | Support Cut | cut by attack |
| 07 | Basic Convoy | con over one sea |
| 08 | Convoy Disrupted | convoyer attacked |
| 09 | Chain of Three | circular moves (k4) |
| 10 | Dislodgement | dislodge visualization |
| 11 | Pattfield | hatching demo |
| 12 | Subfield Resolution | F Spa → MID via SpS |
| 13 | Invalid Move (GEO) | `holds_no_support` behavior |
| 14 | Invalid Support (GEO) | `holds_supportable` behavior |

---

## 7. Test Strategy and Acceptance Criteria

### 7.1 Test pyramid

```
   [DipNet Sweep]          ~500K cases (quantitative)
        ↑
   [DATC Tests]            ~200 cases (compliance)
        ↑
   [DDL Examples]          ~50 cases (docs = tests)
        ↑
   [Phase Integration]     per phase + orchestrator
        ↑
   [Unit Tests]            per rule
```

### 7.2 Acceptance criteria

| Phase | Criterion | Measurement |
|-------|-----------|-------------|
| `eval/` refactor | no behavior change | existing tests green |
| MapProtocol + StandardMap | FIELDS readable, every edge retrievable | per-field + per-edge unit tests |
| Geography service | Gilgamesch B.2.6.1 classification correct | DDL examples 13–14 green, diagnostic trail complete |
| Syntax service | strike + hold-default per B.4.2 | unit tests per SYN-XXX rule |
| Conflict + `order_geo_info` | B.4.2.9 vs B.4.2.10 asymmetry honored | DDL 13 (invalid mve → not hold-supportable) and 14 (invalid sup → hold-supportable) green |
| DATC bug-fixes | 6.D.2 / 6.D.3 / 6.F.1 | each analyzed, fix-or-switch decided, test green |
| DipNet quota | PASS ≥ 80 %, INCONCLUSIVE ≤ 20 % on 100-game sample | `make test-dipnet-quick` reporter |
| Round orchestrator | end-to-end identical to solo calls | integration test with shared input |
| FastAPI endpoints | each service via HTTP | `httpx`-based API test per endpoint |
| DDL renderer | PNG generated for all examples | `make examples-check` green in CI |

### 7.3 CI layout

```
ci:
  - lint          # ruff + mypy
  - unit          # pytest -m unit
  - integration   # pytest -m integration
  - dwex          # make examples-check
  - datc          # pytest tests/test_conflict_datc.py
  - dipnet-quick  # make test-dipnet-quick (≤ 5 min)
  - dipnet-full   # nightly, ≤ 60 min
```

---

## 8. Roadmap

### 8.1 Phases and dependencies

```
P0  Refactor groundwork              ─┐
    ├─ eval/ rename                   │
    ├─ geo_model.py stub              │
    ├─ diag.py                        │
    └─ Switches.strict_unit_types     │
                                      │
P1  DDL renderer                     ─┤   parallel with P2
    ├─ parser + models                │
    ├─ to_situation / to_inline_map   │
    ├─ render_png                     │
    └─ first 5 smoke examples         │
                                      │
P2  MapProtocol + StandardMap        ─┤   parallel with P1
    ├─ standard.json + JSON loader    │
    ├─ fields-to-json converter       │
    ├─ MapRef                         │
    └─ map registry                   │
                                      ▼
P3  Geography service                ─┐   needs P2
    ├─ OrderGeoInfo                   │
    ├─ rules GEO-001..010             │
    ├─ ConvoyGraph extraction         │
    └─ diagnostic trail               │
                                      ▼
P4  Conflicter ↔ order_geo_info      ─┐   needs P3
    ├─ parser consumes geo            │
    ├─ B.4.2.9 vs B.4.2.10 wiring     │
    └─ DDL 13–14 green                │
                                      ▼
P5  Syntax service                   ─┐   needs P2
    ├─ rules SYN-001..008             │
    ├─ hold-default                   │
    └─ diagnostic trail               │
                                      │
P6  Round orchestrator               ─┤   needs P3+P4+P5
    └─ FastAPI app + endpoints        │
                                      │
P7  DATC bug analysis                ─┤   independent, parallel from P0
    ├─ 6.D.2 / 6.D.3 / 6.F.1          │
    └─ fix or switch                  │
                                      │
P8  DipNet cluster analysis          ─┤   needs P3 (geography reduces ?-rate)
    ├─ cluster reporter               │
    └─ top-N pattern fixes            │
                                      │
P9  DDL examples sweep               ─┘   continuous from P1
    ├─ complete list 01–14            │
    ├─ DATC tests as DDL              │
    └─ EXAMPLES.md generator          │

Research stream (parallel):
R-PBM-1  Convoy validity in DE-PBM         before GEO-005/006
R-PBM-2  Geographic support cutting        before refining GEO-004
R-PBM-3  Conflicter on unknown_field       before P4
```

### 8.2 Out of scope (explicit)

- Retreat resolution
- Build / Disband / Supply-center counting
- Multi-variant maps (1898, Britain, …)
- Gilgamesch-only extras (Erscheinungen, Magie, Furten, fly, Transmitter, …)
- Performance optimization
- Frontend UI (third-party concern)
- Authentication / sessions in the service layer
- Async / concurrent order submission

### 8.3 Success metrics

The project is successful when:

1. `syntax`, `geography`, `conflict` are individually callable via HTTP.
2. DipNet PASS rate ≥ 80 % on the 100-game sample (up from 19 %). The current 51 % INCONCLUSIVE must collapse to ≤ 10 % (Geography classifies the void cases), and the 29 % FAIL must collapse to ≤ 10 % (cluster-driven bug fixes).
3. DATC 6.D.2 / 6.D.3 / 6.F.1 each documented (fixed or switch-gated).
4. 14 DDL examples exist as living docs + tests.
5. The Conflict Resolver consumes `order_geo_info` correctly.
6. No file in git references the legacy private sources.

---

## 9. Appendices

### 9.1 Cited Gilgamesch rules

- **B.2.6.1** "Der gültige Bewegungsbefehl" — formal + geographic preconditions.
- **B.2.6.2** "Der wirksame Bewegungsbefehl" — magic / phenomenon override layer (out of scope).
- **B.2.6.3** "Der durchgesetzte Bewegungsbefehl" — won the conflict.
- **B.3.1.1** — Support requires direct neighbor reach, **not** via convoy or furt (Fn. 4).
- **B.3.1.2** — Hold-support requires the supported unit to lack a valid movement order.
- **B.3.2.1 / .5 / .14** — Convoy preconditions; explicit `[Convoy]` flag semantics.
- **B.4.2.9** — Invalid `mve` (bad/missing fields) has no effect, unit is **not** hold-supportable.
- **B.4.2.10** — Invalid `hld`/`sup`/`con` makes the unit hold, **is** hold-supportable.
- **C.2.3** — Head-to-head exception for convoy / fly / transmitter.

### 9.2 Open research items

- R-PBM-1 — Convoy validity edge cases per Schröpl/Kautzsch.
- R-PBM-2 — Geographic support cutting in PBM tradition.
- R-PBM-3 — Conflicter behavior on `unknown_field` markers.

### 9.3 Glossary

- **Superfield / Subfield** — `Spa` is the superfield, `SpN`/`SpS` are subfields. Conflict Resolver sees only superfields.
- **gültig / wirksam / durchgesetzt** — Three-stage cascade per Gilgamesch B.2.6 (valid / effective / enforced).
- **Pattfield** — Territory unavailable for retreats due to a stand-off.
- **PBM** — Postspiel-by-mail (German Diplomacy zine tradition).
- **DDL** — Diplomacy Diagram Language (this project's text-to-PNG DSL).
- **DipNet** — Reference dataset from `diplomacy-research`, 33 279 games used for quantitative regression.
