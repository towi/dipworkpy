# DipworkPy Implementation Plan

> **Status: COMPLETE (2026-05-13)** — All 10 phases (P0..P9) executed via subagent-driven-development.
> Execution range: commits `d6acfd0d` (P0.1 rename) through `7426d6d` (P8 final fix). 47 commits total.
> Outcomes: DATC 10/10, DipNet 96.4 % / 94.9 % (100/1000 sample), 14 DDL examples, full HTTP surface.
> Status snapshot with deferred items: `docs/superpowers/STATUS-2026-05-13.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-architect DipworkPy into a set of independently callable HTTP services (Syntax, Geography, Conflict), introduce a FIELDS-based Map layer with PBM-correct order classification, add a DDL renderer for living documentation and tests, and lift DipNet PASS rate from 19 % to ≥ 80 %.

**Architecture:** Three pure-function services (`syntax_phase`, `geography_phase`, `conflict_game`) composable via a thin orchestrator. Geography classifies orders per Gilgamesch B.2.6.1 and emits `OrderGeoInfo` markers; the conflict resolver consumes the markers to preserve the B.4.2.9/B.4.2.10 asymmetry (invalid `mve` → unit stays but not hold-supportable; invalid `hld`/`sup`/`con` → unit holds and is hold-supportable). The Map is a JSON-loaded `MapProtocol` implementation with separate army/fleet/convoy passability per directed edge.

**Tech Stack:** Python 3.9+, Pydantic 2.x, FastAPI, pytest, ruff, mypy, matplotlib (DDL renderer), Poetry.

**Reference Spec:** `docs/superpowers/specs/2026-05-12-dipworkpy-comprehensive-design.md`

---

## Parallelism Map

```
P0 Foundation (sequential)
   │
   ├── P1 DDL Renderer ─────────┐
   ├── P2 Map Layer ────────────┤   parallel
   └── P7 DATC Bug Analysis ────┘
                │
   ┌────────────┴────────────┐
   │                         │
   P3 Geography (needs P2)   P5 Syntax (needs P2) — parallel
                │
   P4 Conflicter integration (needs P3)
                │
   P6 Round Orchestrator + FastAPI (needs P3+P4+P5)
                │
   P8 DipNet Cluster Analysis (needs P3+P4 to reduce ?-rate)
   P9 DDL Examples Sweep (continuous from P1)
```

When dispatching subagents: tasks within the same phase that touch disjoint files can run in parallel. Tasks across `P1`/`P2`/`P7` are always independent.

---

## File Structure

```
project/dipworkpy/
  model.py                       # MODIFY: + via_convoy:bool placeholder, Switches.strict_unit_types
  geo_model.py                   # CREATE: shared geo types
  diag.py                        # CREATE: Diagnostic
  eval/                          # RENAME from dip_eval/
    eval_model.py
    eval_common.py
    eval_k0.py .. eval_k4.py
    __init__.py
  syntax/                        # CREATE
    __init__.py
    model.py
    rules.py
    service.py
    api.py
  geography/                     # CREATE
    __init__.py
    model.py
    rules.py
    convoy.py
    coast.py
    service.py
    api.py
    map/
      __init__.py
      protocol.py
      standard.py
      inline.py
      registry.py
      data/
        standard.json
  conflict/                      # CREATE
    __init__.py
    model.py
    parser.py
    writer.py
    service.py
    api.py
  round/                         # CREATE
    __init__.py
    orchestrator.py
    api.py
  api_app.py                     # CREATE
  tools/                         # CREATE
    __init__.py
    fields_to_json.py
    dwex/
      __init__.py
      lang.py
      model.py
      to_situation.py
      to_map.py
      render_png.py
      generate_index.py
      cli.py
project/tests/
  test_geo_model.py              # CREATE
  test_diag.py                   # CREATE
  test_map_protocol.py           # CREATE
  test_standard_map.py           # CREATE
  test_inline_map.py             # CREATE
  test_geography_service.py      # CREATE (parametrized per rule)
  test_syntax_service.py         # CREATE (parametrized per rule)
  test_conflict_geo_info.py      # CREATE (B.4.2.9/.10 asymmetry)
  test_round_orchestrator.py     # CREATE
  test_dwex_lang.py              # CREATE
  test_dwex_render.py            # CREATE
  test_dwex_examples.py          # CREATE (parametrized over .dwex files)
  test_api_endpoints.py          # CREATE
project/doc/examples/
  README.md
  dwex/
    01_basic_hold.dwex .. 14_invalid_support.dwex
    *.png
project/doc/
  EXAMPLES.md                    # generated
  DATC_ANALYSIS.md               # P7 output
  DIPNET_CLUSTERS.md             # P8 output
  PBM_RULES.md                   # R-PBM research output
```

---

## Conventions for all tasks

- **TDD:** Write the failing test, run to verify it fails, implement minimum code, run to verify it passes, then commit.
- **One concept per commit.** Conventional-Commits style headline: `feat(geography): GEO-001 missing-destination rule`.
- **Co-Authored-By trailer** on every commit:
  ```
  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  ```
- **Working directory** is the repo root. All `poetry run` commands run from `project/`. Many existing test commands chdir, follow the pattern.
- **Run from `project/`:** prefix shell commands with `cd project && ` or use `make -C project`.
- **Imports:** Python `from dipworkpy.X import Y` style. After P0 task 1, `from dipworkpy.eval import ...` replaces `from dipworkpy.dip_eval import ...`.
- **Pre-commit lint check:** before committing, run `cd project && poetry run ruff check . && poetry run mypy .` — fix issues before staging.

---

## Phase P0: Foundation

These tasks must complete first. They are mostly mechanical and unlock parallel work in P1/P2/P5/P7.

### Task P0.1: Rename `dip_eval/` → `eval/`

**Files:**
- Rename: `project/dipworkpy/dip_eval/` → `project/dipworkpy/eval/`
- Modify: all imports of `dipworkpy.dip_eval` across the repo

- [x] **Step 1: Inspect current import surface**

Run: `cd project && grep -rn "dip_eval" --include='*.py' .`
Expected: list of every file importing from `dip_eval`. Note the file paths.

- [x] **Step 2: Rename the directory**

Run: `cd project && git mv dipworkpy/dip_eval dipworkpy/eval`
Expected: directory renamed, git tracks the rename.

- [x] **Step 3: Update imports across the repo**

Run: `cd project && grep -rl "dip_eval" --include='*.py' . | xargs sed -i 's/dip_eval/eval/g'`
Expected: every reference to `dip_eval` now reads `eval`.

- [x] **Step 4: Update package `__init__.py` re-exports**

Modify: `project/dipworkpy/eval/__init__.py` — search/replace any internal `dip_eval` self-references. Replace any "dip_eval" string literal (e.g. in `__all__`, logger names) with "eval".

- [x] **Step 5: Run full test suite**

Run: `cd project && poetry run python -m pytest tests/ -x`
Expected: all tests that passed before still pass. Zero behavior change.

- [x] **Step 6: Run lint and type-check**

Run: `cd project && poetry run ruff check . && poetry run mypy .`
Expected: clean.

- [x] **Step 7: Commit**

```bash
cd project && git add -A
git commit -m "$(cat <<'EOF'
refactor: rename dip_eval/ to eval/

The original name mirrored a 1993 Pascal module label. Now that eval is one
of several first-class phase services (geography, syntax, conflict, ...) it
sits as a peer at the top level of dipworkpy/.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P0.2: Create `geo_model.py` (shared geo types)

**Files:**
- Create: `project/dipworkpy/geo_model.py`
- Test: `project/tests/test_geo_model.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_geo_model.py`:

```python
"""Tests for shared geo-model types."""
import pytest
from pydantic import ValidationError

from dipworkpy.geo_model import (
    FieldType, Passable, Edge, MapDefinition, MapRef,
    OrderGeoInfo, ConvoyGraph,
)


def test_field_type_enum_values():
    assert FieldType.LA.value == "LA"
    assert FieldType.LCB.value == "LCB"
    assert FieldType.LCA.value == "LCA"
    assert FieldType.LC.value == "LC"
    assert FieldType.LCF.value == "LCF"
    assert FieldType.L.value == "L"
    assert FieldType.O.value == "O"
    assert FieldType.COL.value == "COL"


def test_passable_enum_values():
    assert Passable.YES.value == "ja"
    assert Passable.NO.value == "nein"
    assert Passable.NA.value == "-"
    assert Passable.IMP.value == "imp"


def test_edge_with_simple_passable():
    e = Edge(army=Passable.YES, fleet=Passable.NO, convoy_move=Passable.YES)
    assert e.army == Passable.YES


def test_edge_with_subfield_required_for_fleet():
    e = Edge(army=Passable.YES, fleet="SpN", convoy_move=Passable.YES)
    assert e.fleet == "SpN"


def test_map_ref_defaults_to_standard():
    r = MapRef()
    assert r.map_id == "standard"
    assert r.inline_map is None


def test_map_ref_accepts_inline():
    m = MapDefinition(fields={}, edges={})
    r = MapRef(inline_map=m)
    assert r.inline_map is m


def test_order_geo_info_moves():
    info = OrderGeoInfo(order_index=0, is_valid=True, effective_behavior="moves")
    assert info.is_valid is True
    assert info.effective_behavior == "moves"


def test_order_geo_info_invalid_mve_holds_no_support():
    info = OrderGeoInfo(
        order_index=2, is_valid=False,
        invalidity_code="GEO-003", invalidity_reason="not reachable",
        effective_behavior="holds_no_support",
    )
    assert info.effective_behavior == "holds_no_support"


def test_order_geo_info_invalid_sup_holds_supportable():
    info = OrderGeoInfo(
        order_index=1, is_valid=False,
        invalidity_code="GEO-004",
        effective_behavior="holds_supportable",
    )
    assert info.effective_behavior == "holds_supportable"


def test_order_geo_info_rejects_unknown_behavior():
    with pytest.raises(ValidationError):
        OrderGeoInfo(order_index=0, is_valid=True, effective_behavior="floats")


def test_convoy_graph_defaults_empty():
    g = ConvoyGraph()
    assert g.sea_edges == set()
    assert g.coastal_edges == set()
    assert g.convoyer_fields == set()
    assert g.cmove_candidates == set()
```

- [x] **Step 2: Verify the tests fail (module doesn't exist yet)**

Run: `cd project && poetry run python -m pytest tests/test_geo_model.py -v`
Expected: `ModuleNotFoundError: No module named 'dipworkpy.geo_model'`.

- [x] **Step 3: Implement the module**

Create `project/dipworkpy/geo_model.py`:

```python
"""Shared geographic data types.

These types are the interface contract between geography/, syntax/, and
conflict/ services. None of them carries behavior - they are pure data.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Field-type classification, mirroring the FIELDS-spec tags."""
    LA  = "LA"
    LCB = "LCB"
    LCA = "LCA"
    LC  = "LC"
    LCF = "LCF"
    L   = "L"
    O   = "O"
    COL = "COL"


class Passable(str, Enum):
    """Passability values for a directed map edge.

    Per the FIELDS spec, an edge has three independent passability values
    (army, fleet, convoy_move). 'imp' marks an unreachable-without-coast
    case; a literal subfield name (e.g. 'SpN') marks a coast-required move.
    """
    YES = "ja"
    NO  = "nein"
    NA  = "-"
    IMP = "imp"


class Edge(BaseModel):
    """A directed map edge with separate passability per unit kind.

    `army` and `fleet` may carry a literal subfield-name string instead of
    a Passable value, indicating the move must specify that coast.
    """
    army: Union[Passable, str]
    fleet: Union[Passable, str]
    convoy_move: Passable


class FieldDef(BaseModel):
    """Definition of a single field."""
    name: str
    type: FieldType
    sub_of: Optional[str] = None
    is_supply_center: bool = False
    home_of: Optional[str] = None
    pos: Optional[Tuple[float, float]] = None


class MapDefinition(BaseModel):
    """A complete map definition - the inline-map shape passed in MapRef."""
    fields: Dict[str, FieldDef] = Field(default_factory=dict)
    edges: Dict[Tuple[str, str], Edge] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class MapRef(BaseModel):
    """Reference to a map: either registered map_id or inline definition."""
    map_id: Optional[str] = "standard"
    inline_map: Optional[MapDefinition] = None


class OrderGeoInfo(BaseModel):
    """Per-order classification produced by the Geography service.

    Travels alongside the orders list to the Conflict Resolver. Indexed by
    order position in the parallel orders list.
    """
    order_index: int
    is_valid: bool
    invalidity_code: Optional[str] = None
    invalidity_reason: Optional[str] = None
    effective_behavior: Literal[
        "moves",
        "holds_no_support",
        "holds_supportable",
        "holds_explicit",
    ]
    resolved_coast: Optional[str] = None
    is_convoy_move: bool = False
    explicit_via_convoy: bool = False


class ConvoyGraph(BaseModel):
    """Pre-extracted convoy-relevant subgraph.

    The Conflict Resolver does its own BFS on this graph; Geography only
    delivers the topology and the convoyer set.
    """
    sea_edges: Set[Tuple[str, str]] = Field(default_factory=set)
    coastal_edges: Set[Tuple[str, str]] = Field(default_factory=set)
    convoyer_fields: Set[str] = Field(default_factory=set)
    cmove_candidates: Set[int] = Field(default_factory=set)
```

- [x] **Step 4: Run tests to verify pass**

Run: `cd project && poetry run python -m pytest tests/test_geo_model.py -v`
Expected: all 12 tests pass.

- [x] **Step 5: Lint + type-check**

Run: `cd project && poetry run ruff check dipworkpy/geo_model.py tests/test_geo_model.py && poetry run mypy dipworkpy/geo_model.py`
Expected: clean.

- [x] **Step 6: Commit**

```bash
cd project && git add dipworkpy/geo_model.py tests/test_geo_model.py
git commit -m "$(cat <<'EOF'
feat(geo): add shared geo-model types

Defines the data contract between geography, syntax, conflict and tools.
OrderGeoInfo.effective_behavior is the carrier for the PBM asymmetry
(invalid mve -> holds_no_support, invalid hld/sup/con -> holds_supportable),
which is what makes the Conflict Resolver able to honor Gilgamesch B.4.2.9
vs B.4.2.10 without rewriting orders.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P0.3: Create `diag.py` (Diagnostic type)

**Files:**
- Create: `project/dipworkpy/diag.py`
- Test: `project/tests/test_diag.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_diag.py`:

```python
import pytest
from pydantic import ValidationError
from dipworkpy.diag import Diagnostic


def test_diagnostic_minimal():
    d = Diagnostic(phase="geography", rule="GEO-001", severity="info",
                   message="ok")
    assert d.phase == "geography"
    assert d.order_index is None
    assert d.details == {}


def test_diagnostic_with_order_index_and_details():
    d = Diagnostic(
        phase="syntax", rule="SYN-005", severity="correction",
        order_index=3, message="double order on Vie",
        details={"existing": "mve Mun", "incoming": "hld"},
    )
    assert d.order_index == 3
    assert d.details["existing"] == "mve Mun"


def test_diagnostic_rejects_unknown_phase():
    with pytest.raises(ValidationError):
        Diagnostic(phase="magic", rule="X", severity="info", message="")


def test_diagnostic_rejects_unknown_severity():
    with pytest.raises(ValidationError):
        Diagnostic(phase="syntax", rule="X", severity="boom", message="")
```

- [x] **Step 2: Verify tests fail**

Run: `cd project && poetry run python -m pytest tests/test_diag.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement**

Create `project/dipworkpy/diag.py`:

```python
"""Diagnostic - structured audit-trail entry produced by every service."""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class Diagnostic(BaseModel):
    """One structured entry in a phase's audit trail.

    Every rule evaluation emits one Diagnostic - even no-ops with
    severity='info' - so a consuming UI can show *which* rules were checked,
    not just which fired.
    """
    phase: Literal["syntax", "geography", "conflict", "round"]
    rule: str
    severity: Literal["info", "warning", "correction", "error"]
    order_index: Optional[int] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
```

- [x] **Step 4: Run tests**

Run: `cd project && poetry run python -m pytest tests/test_diag.py -v`
Expected: 4 tests pass.

- [x] **Step 5: Lint + type-check**

Run: `cd project && poetry run ruff check dipworkpy/diag.py tests/test_diag.py && poetry run mypy dipworkpy/diag.py`

- [x] **Step 6: Commit**

```bash
cd project && git add dipworkpy/diag.py tests/test_diag.py
git commit -m "$(cat <<'EOF'
feat: add Diagnostic type for service audit trails

Every phase emits one Diagnostic per rule evaluated (incl. no-op info-level
entries), so consumers see not only what was corrected but *which rules
were checked* and why each verdict was reached.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P0.4: Add `Switches.strict_unit_types`

**Files:**
- Modify: `project/dipworkpy/model.py`
- Modify: `project/tests/test_model.py` (or create new test if absent)

- [x] **Step 1: Locate the Switches model**

Run: `cd project && grep -n "class Switches" dipworkpy/model.py`
Expected: one match. Note line number.

- [x] **Step 2: Write failing test**

Add to `project/tests/test_model.py` (create the file if missing with minimal `from dipworkpy.model import Switches`):

```python
def test_switches_strict_unit_types_default_false():
    from dipworkpy.model import Switches
    assert Switches().strict_unit_types is False


def test_switches_strict_unit_types_can_be_enabled():
    from dipworkpy.model import Switches
    s = Switches(strict_unit_types=True)
    assert s.strict_unit_types is True
```

- [x] **Step 3: Run test to verify failure**

Run: `cd project && poetry run python -m pytest tests/test_model.py::test_switches_strict_unit_types_default_false -v`
Expected: AttributeError or ValidationError - field doesn't exist.

- [x] **Step 4: Implement the field**

Modify `project/dipworkpy/model.py`. Inside `class Switches(BaseModel):`, add after the existing fields:

```python
    strict_unit_types: Optional[bool] = Field(
        default=False,
        description=(
            "If True, unknown unit types and unit/field-type mismatches "
            "trigger SYN-002/SYN-007 strikes. Default off for std-Diplomacy "
            "where unit type is irrelevant for the conflict algorithm."
        ),
    )
```

- [x] **Step 5: Run tests**

Run: `cd project && poetry run python -m pytest tests/test_model.py -v`
Expected: new tests pass, existing tests remain green.

- [x] **Step 6: Lint + type-check**

Run: `cd project && poetry run ruff check dipworkpy/model.py && poetry run mypy dipworkpy/model.py`

- [x] **Step 7: Commit**

```bash
cd project && git add dipworkpy/model.py tests/test_model.py
git commit -m "$(cat <<'EOF'
feat(model): add Switches.strict_unit_types

Default False mirrors std-Diplomacy semantics where the conflict resolver
treats A and F identically w.r.t. strength. Enabling the switch makes
SYN-002/SYN-007 active, which lets the syntax phase disambiguate
double-orders by unit type (Gilgamesch-style strict mode).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P0.5: P0 smoke-check — full suite + lint clean

**Files:** none modified; verification only.

- [x] **Step 1: Run full test suite**

Run: `cd project && poetry run python -m pytest tests/ -x`
Expected: all tests pass.

- [x] **Step 2: Run lint**

Run: `cd project && poetry run ruff check . && poetry run mypy .`
Expected: clean.

- [x] **Step 3: Run DATC test set**

Run: `cd project && make test-datc`
Expected: same 7/10 pass / 3/10 fail count as before P0 (no behavior change).

- [x] **Step 4: Tag the foundation milestone (no commit, just verify)**

Run: `git log --oneline -10`
Expected: P0.1-P0.4 commits visible, nothing else uncommitted.

---


## Phase P2: Map Layer

Parallel to P1. Provides the FIELDS-shaped map data and the `MapProtocol` abstraction every other service depends on.

### Task P2.1: Define `MapProtocol`

**Files:**
- Create: `project/dipworkpy/geography/__init__.py` (empty)
- Create: `project/dipworkpy/geography/map/__init__.py` (empty)
- Create: `project/dipworkpy/geography/map/protocol.py`
- Test: `project/tests/test_map_protocol.py`

- [x] **Step 1: Write failing test**

Create `project/tests/test_map_protocol.py`:

```python
"""Tests that the MapProtocol Protocol is correctly defined."""
from typing import get_type_hints
from dipworkpy.geography.map.protocol import MapProtocol


def test_protocol_has_required_methods():
    expected_methods = {
        "field_exists", "field_type", "superfield_of", "subfields_of",
        "is_supply_center", "home_center_of",
        "edge", "neighbors",
        "army_passable", "fleet_passable", "convoy_passable",
    }
    actual_methods = {m for m in dir(MapProtocol) if not m.startswith("_")}
    missing = expected_methods - actual_methods
    assert not missing, f"MapProtocol missing methods: {missing}"


def test_protocol_has_map_id_attribute():
    assert "map_id" in get_type_hints(MapProtocol)
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_map_protocol.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement protocol**

Create `project/dipworkpy/geography/map/protocol.py`:

```python
"""MapProtocol - the abstract contract a map implementation must satisfy.

Uses PEP 544 Protocol so any conforming object works without inheritance.
"""
from __future__ import annotations

from typing import Optional, Protocol, Set, Union, runtime_checkable

from dipworkpy.geo_model import Edge, FieldType, Passable


@runtime_checkable
class MapProtocol(Protocol):
    """Abstract map. Implementations: StandardMap, InlineMap."""
    map_id: str

    # Fields
    def field_exists(self, fld: str) -> bool: ...
    def field_type(self, fld: str) -> FieldType: ...
    def superfield_of(self, fld: str) -> str: ...
    def subfields_of(self, fld: str) -> list[str]: ...
    def is_supply_center(self, fld: str) -> bool: ...
    def home_center_of(self, fld: str) -> Optional[str]: ...

    # Edges
    def edge(self, frm: str, to: str) -> Optional[Edge]: ...
    def neighbors(self, fld: str) -> Set[str]: ...

    # Convenience derived from edge()
    def army_passable(self, frm: str, to: str) -> bool: ...
    def fleet_passable(self, frm: str, to: str) -> Union[Passable, str]: ...
    def convoy_passable(self, frm: str, to: str) -> bool: ...
```

- [x] **Step 4: Run tests**

Run: `cd project && poetry run python -m pytest tests/test_map_protocol.py -v`
Expected: 2 tests pass.

- [x] **Step 5: Lint + commit**

```bash
cd project && poetry run ruff check dipworkpy/geography/ tests/test_map_protocol.py
git add dipworkpy/geography/ tests/test_map_protocol.py
git commit -m "$(cat <<'EOF'
feat(geography): define MapProtocol

PEP 544 Protocol with 11 methods covering field metadata, subfield-coast
relations, and per-edge army/fleet/convoy passability. Implementations
(StandardMap, InlineMap) plug in via duck typing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P2.2: Author `standard.json` (Standard Diplomacy map)

**Files:**
- Create: `project/dipworkpy/geography/map/data/__init__.py` (empty)
- Create: `project/dipworkpy/geography/map/data/standard.json`
- Test: `project/tests/test_standard_map_data.py`

- [x] **Step 1: Write failing schema test**

Create `project/tests/test_standard_map_data.py`:

```python
"""Smoke-test the bundled standard.json - structural sanity only."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "dipworkpy/geography/map/data/standard.json"


def test_standard_json_exists():
    assert DATA.exists(), f"missing {DATA}"


def test_standard_json_parses():
    with open(DATA) as f:
        m = json.load(f)
    assert "fields" in m
    assert "edges" in m


def test_standard_has_all_34_supply_centers():
    with open(DATA) as f:
        m = json.load(f)
    sc_count = sum(1 for f in m["fields"].values() if f.get("is_supply_center"))
    assert sc_count == 34, f"expected 34 supply centers, got {sc_count}"


def test_standard_has_subfields_for_split_coasts():
    with open(DATA) as f:
        m = json.load(f)
    fields = m["fields"]
    for sup, subs in [("Spa", ["SpN", "SpS"]), ("Pet", ["PeN", "PeS"]),
                      ("Bul", ["BuE", "BuS"])]:
        assert sup in fields, f"missing superfield {sup}"
        for sub in subs:
            assert sub in fields, f"missing subfield {sub}"
            assert fields[sub]["sub_of"] == sup


def test_standard_edges_use_passable_grammar():
    with open(DATA) as f:
        m = json.load(f)
    valid_passable = {"ja", "nein", "-", "imp"}
    for edge_key, e in m["edges"].items():
        for k in ["army", "fleet", "convoy_move"]:
            v = e[k]
            # Either a Passable string, or a subfield name (coast-required)
            assert v in valid_passable or (isinstance(v, str) and len(v) <= 4), \
                f"bad {k} on {edge_key}: {v!r}"
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_standard_map_data.py -v`
Expected: all four tests fail (file missing).

- [x] **Step 3: Author `standard.json`**

**Recommended path:** Complete Task P2.5 first (builds `fields_to_json.py`), then run the converter against any local FIELDS-spec text file the maintainer has on disk. One command produces the full JSON.

```bash
cd project && poetry run python -m dipworkpy.tools.fields_to_json \
    /path/to/FIELDS-source.txt \
    dipworkpy/geography/map/data/standard.json
```

**Fallback path:** Hand-author the JSON using the template below as a starting point. Cross-reference adjacency lists from any open-source Diplomacy implementation (`pydiplomacy`, `diplomacy-py`, `stpsyr`, …) and translate into the per-direction Edge schema. Expect 60-90 min for careful entry + verification against the schema tests above.

Template structure:

```json
{
  "map_id": "standard",
  "fields": {
    "Vie": {"type": "LA", "is_supply_center": true, "home_of": "Au", "pos": [760, 765]},
    "Bud": {"type": "LA", "is_supply_center": true, "home_of": "Au", "pos": [860, 810]},
    "Tri": {"type": "LCB", "is_supply_center": true, "home_of": "Au", "pos": [750, 870]},
    "Boh": {"type": "L", "pos": [710, 710]},
    "Tyr": {"type": "L", "pos": [660, 800]},
    "Gal": {"type": "L", "pos": [910, 725]},
    "Spa": {"type": "LC", "is_supply_center": true, "pos": [270, 950]},
    "SpN": {"type": "LC", "sub_of": "Spa", "pos": [285, 855]},
    "SpS": {"type": "LC", "sub_of": "Spa", "pos": [280, 1025]},
    "Pet": {"type": "LCA", "is_supply_center": true, "home_of": "Ru", "pos": [1060, 325]},
    "PeN": {"type": "LCF", "sub_of": "Pet", "home_of": "Ru", "pos": [1090, 245]},
    "PeS": {"type": "LCF", "sub_of": "Pet", "home_of": "Ru", "pos": [980, 405]},
    "Bul": {"type": "LC", "is_supply_center": true, "pos": [940, 942]},
    "BuE": {"type": "LC", "sub_of": "Bul", "pos": [980, 935]},
    "BuS": {"type": "LC", "sub_of": "Bul", "pos": [952, 978]},
    "NTH": {"type": "O", "pos": [530, 490]},
    "Sui": {"type": "L", "pos": [575, 800]}
  },
  "edges": {
    "Vie:Boh": {"army": "ja", "fleet": "-", "convoy_move": "nein"},
    "Vie:Bud": {"army": "ja", "fleet": "-", "convoy_move": "nein"},
    "Vie:Gal": {"army": "ja", "fleet": "-", "convoy_move": "nein"},
    "Vie:Tri": {"army": "ja", "fleet": "-", "convoy_move": "nein"},
    "Vie:Tyr": {"army": "ja", "fleet": "-", "convoy_move": "nein"},
    "Boh:Mun": {"army": "ja", "fleet": "-", "convoy_move": "nein"}
  }
}
```

Continue with all 75 fields and all edges. Edge keys are `"from:to"` (directed; bidirectional adjacencies need both `"A:B"` and `"B:A"`).

**Field-type cheatsheet** for the standard map:
- `LA`: landlocked supply-center capitals (Vie, Bud, Par, Mun, Mos, War)
- `LCB`: coastal supply centers without split coast (Tri, Lpl, Lon, Edi, Bre, Mar, Kie, Ber, Rom, Nap, Ven, Con, Ank, Smy)
- `LCA`: supply centers with split coasts (Pet, Seb)
- `LCF`: subfield entries of LCA (PeN, PeS — Seb has no subfields in standard map, but Pet does)
- `LC`: single-coast non-supply or neutral SCs (Nor, Bel, Tun, Swe, Den, Hol, Gre, Bul, Rum, Spa, Por, Cly, Wal, Yor, Pic, Afr, Syr, Fin, Apu, Liv, Pie, Tus, Arm, Alb, Pru, Gas, and the Spa/Bul subfields)
- `L`: pure inland non-SCs (Ser, Bur, Ruh, Tyr, Ukr, Sil, Boh, Gal, Tyr, Sui)
- `O`: ocean fields (NTH, NWS, ENG, IRI, WMS, LYO, TYS, ION, ADR, AEG, EAS, BLA, BAR, BOT, BAS, SKA, HEL, MID, NAT)

Persisting this canonical map by hand is meticulous work; subagent dispatching this task should expect 60-90 min for careful entry + verification.

- [x] **Step 4: Run schema tests**

Run: `cd project && poetry run python -m pytest tests/test_standard_map_data.py -v`
Expected: all four tests pass. If `test_standard_has_all_34_supply_centers` fails, count: 22 home SCs + 12 neutral SCs (Nor, Swe, Den, Hol, Bel, Por, Spa, Tun, Ser, Gre, Bul, Rum).

- [x] **Step 5: Commit**

```bash
cd project && git add dipworkpy/geography/map/data/ tests/test_standard_map_data.py
git commit -m "$(cat <<'EOF'
feat(geography): bundle standard Diplomacy map as JSON

75 fields + full bidirectional edge set, FIELDS-spec-compatible passability
per army/fleet/convoy_move plus subfield encoding for Spa/Pet/Bul split
coasts. JSON chosen for stdlib parsing, Pydantic round-trip, and diffability.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P2.3: Implement `StandardMap` loader

**Files:**
- Create: `project/dipworkpy/geography/map/standard.py`
- Test: `project/tests/test_standard_map.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_standard_map.py`:

```python
"""Tests for StandardMap - the bundled FIELDS-shape map loader."""
import pytest
from dipworkpy.geography.map.standard import StandardMap
from dipworkpy.geo_model import FieldType, Passable


@pytest.fixture(scope="module")
def m():
    return StandardMap()


def test_field_exists_known(m):
    assert m.field_exists("Vie")
    assert m.field_exists("NTH")


def test_field_exists_unknown(m):
    assert not m.field_exists("ZZZ")


def test_field_type(m):
    assert m.field_type("Vie") == FieldType.LA
    assert m.field_type("NTH") == FieldType.O
    assert m.field_type("Spa") == FieldType.LC


def test_superfield_self_for_non_subfield(m):
    assert m.superfield_of("Vie") == "Vie"
    assert m.superfield_of("Spa") == "Spa"


def test_superfield_for_subfield(m):
    assert m.superfield_of("SpN") == "Spa"
    assert m.superfield_of("SpS") == "Spa"


def test_subfields_of_split_coast(m):
    assert set(m.subfields_of("Spa")) == {"SpN", "SpS"}
    assert set(m.subfields_of("Pet")) == {"PeN", "PeS"}


def test_subfields_of_non_split(m):
    assert m.subfields_of("Vie") == []


def test_neighbors(m):
    nbrs = m.neighbors("Vie")
    assert "Boh" in nbrs
    assert "Bud" in nbrs
    assert "Tyr" in nbrs


def test_edge_returns_none_for_non_adjacent(m):
    assert m.edge("Vie", "Lon") is None


def test_army_passable_basic(m):
    assert m.army_passable("Vie", "Boh") is True
    assert m.army_passable("Vie", "NTH") is False


def test_supply_center_flag(m):
    assert m.is_supply_center("Vie") is True
    assert m.is_supply_center("Boh") is False
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_standard_map.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement StandardMap**

Create `project/dipworkpy/geography/map/standard.py`:

```python
"""StandardMap - loads the bundled standard.json and exposes MapProtocol."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Set, Tuple, Union

from dipworkpy.geo_model import Edge, FieldType, Passable

_DATA_FILE = Path(__file__).parent / "data" / "standard.json"


class StandardMap:
    """Loads the standard map data and serves it through MapProtocol."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.map_id = "standard"
        src = path or _DATA_FILE
        with open(src) as f:
            raw = json.load(f)
        self._fields: Dict[str, dict] = raw["fields"]
        # Edges keyed by "from:to"
        self._edges: Dict[Tuple[str, str], Edge] = {}
        for key, val in raw["edges"].items():
            frm, to = key.split(":", 1)
            self._edges[(frm, to)] = Edge(**val)
        # Pre-compute subfield reverse index
        self._subfields_by_super: Dict[str, list[str]] = {}
        for name, fdef in self._fields.items():
            sub_of = fdef.get("sub_of")
            if sub_of:
                self._subfields_by_super.setdefault(sub_of, []).append(name)

    def field_exists(self, fld: str) -> bool:
        return fld in self._fields

    def field_type(self, fld: str) -> FieldType:
        return FieldType(self._fields[fld]["type"])

    def superfield_of(self, fld: str) -> str:
        return self._fields[fld].get("sub_of") or fld

    def subfields_of(self, fld: str) -> list[str]:
        return list(self._subfields_by_super.get(fld, []))

    def is_supply_center(self, fld: str) -> bool:
        return bool(self._fields[fld].get("is_supply_center", False))

    def home_center_of(self, fld: str) -> Optional[str]:
        return self._fields[fld].get("home_of")

    def edge(self, frm: str, to: str) -> Optional[Edge]:
        return self._edges.get((frm, to))

    def neighbors(self, fld: str) -> Set[str]:
        return {to for (frm, to) in self._edges if frm == fld}

    def army_passable(self, frm: str, to: str) -> bool:
        e = self.edge(frm, to)
        if e is None:
            return False
        return e.army == Passable.YES or isinstance(e.army, str) and e.army not in {
            Passable.NO.value, Passable.NA.value, Passable.IMP.value
        }

    def fleet_passable(self, frm: str, to: str) -> Union[Passable, str]:
        e = self.edge(frm, to)
        if e is None:
            return Passable.NA
        return e.fleet

    def convoy_passable(self, frm: str, to: str) -> bool:
        e = self.edge(frm, to)
        return bool(e) and e.convoy_move == Passable.YES
```

- [x] **Step 4: Run tests**

Run: `cd project && poetry run python -m pytest tests/test_standard_map.py -v`
Expected: 11 tests pass.

- [x] **Step 5: Lint + commit**

```bash
cd project && poetry run ruff check dipworkpy/geography/map/standard.py tests/test_standard_map.py
poetry run mypy dipworkpy/geography/map/standard.py
git add dipworkpy/geography/map/standard.py tests/test_standard_map.py
git commit -m "$(cat <<'EOF'
feat(geography): implement StandardMap loader

Reads bundled standard.json, exposes MapProtocol surface. Pre-computes a
reverse subfield index so subfields_of(Spa) -> [SpN, SpS] is O(1).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P2.4: Implement `InlineMap`

**Files:**
- Create: `project/dipworkpy/geography/map/inline.py`
- Test: `project/tests/test_inline_map.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_inline_map.py`:

```python
from dipworkpy.geo_model import (
    Edge, FieldDef, FieldType, MapDefinition, Passable,
)
from dipworkpy.geography.map.inline import InlineMap


def _three_field_def() -> MapDefinition:
    return MapDefinition(
        fields={
            "A": FieldDef(name="A", type=FieldType.LA),
            "B": FieldDef(name="B", type=FieldType.LA),
            "C": FieldDef(name="C", type=FieldType.O),
        },
        edges={
            ("A", "B"): Edge(army=Passable.YES, fleet=Passable.NA, convoy_move=Passable.NO),
            ("B", "A"): Edge(army=Passable.YES, fleet=Passable.NA, convoy_move=Passable.NO),
            ("A", "C"): Edge(army=Passable.NO, fleet=Passable.YES, convoy_move=Passable.YES),
            ("C", "A"): Edge(army=Passable.NO, fleet=Passable.YES, convoy_move=Passable.YES),
        },
    )


def test_inline_map_field_exists():
    m = InlineMap(_three_field_def(), map_id="t1")
    assert m.field_exists("A")
    assert not m.field_exists("Z")


def test_inline_map_neighbors():
    m = InlineMap(_three_field_def())
    assert m.neighbors("A") == {"B", "C"}


def test_inline_map_army_passable():
    m = InlineMap(_three_field_def())
    assert m.army_passable("A", "B") is True
    assert m.army_passable("A", "C") is False


def test_inline_map_default_map_id():
    m = InlineMap(_three_field_def())
    assert m.map_id == "inline"
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_inline_map.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement InlineMap**

Create `project/dipworkpy/geography/map/inline.py`:

```python
"""InlineMap - MapProtocol implementation from an in-memory MapDefinition.

Used by DDL test fixtures and custom variant requests.
"""
from __future__ import annotations

from typing import Optional, Set, Union

from dipworkpy.geo_model import Edge, FieldType, MapDefinition, Passable


class InlineMap:
    def __init__(self, mdef: MapDefinition, map_id: str = "inline") -> None:
        self.map_id = map_id
        self._mdef = mdef
        self._subfields_by_super: dict[str, list[str]] = {}
        for name, fd in mdef.fields.items():
            if fd.sub_of:
                self._subfields_by_super.setdefault(fd.sub_of, []).append(name)

    def field_exists(self, fld: str) -> bool:
        return fld in self._mdef.fields

    def field_type(self, fld: str) -> FieldType:
        return self._mdef.fields[fld].type

    def superfield_of(self, fld: str) -> str:
        fd = self._mdef.fields[fld]
        return fd.sub_of or fld

    def subfields_of(self, fld: str) -> list[str]:
        return list(self._subfields_by_super.get(fld, []))

    def is_supply_center(self, fld: str) -> bool:
        return self._mdef.fields[fld].is_supply_center

    def home_center_of(self, fld: str) -> Optional[str]:
        return self._mdef.fields[fld].home_of

    def edge(self, frm: str, to: str) -> Optional[Edge]:
        return self._mdef.edges.get((frm, to))

    def neighbors(self, fld: str) -> Set[str]:
        return {to for (frm, to) in self._mdef.edges if frm == fld}

    def army_passable(self, frm: str, to: str) -> bool:
        e = self.edge(frm, to)
        if e is None:
            return False
        return e.army == Passable.YES

    def fleet_passable(self, frm: str, to: str) -> Union[Passable, str]:
        e = self.edge(frm, to)
        if e is None:
            return Passable.NA
        return e.fleet

    def convoy_passable(self, frm: str, to: str) -> bool:
        e = self.edge(frm, to)
        return bool(e) and e.convoy_move == Passable.YES
```

- [x] **Step 4: Run tests + lint**

Run: `cd project && poetry run python -m pytest tests/test_inline_map.py -v && poetry run ruff check dipworkpy/geography/map/inline.py tests/test_inline_map.py && poetry run mypy dipworkpy/geography/map/inline.py`
Expected: 4 tests pass, lint clean.

- [x] **Step 5: Commit**

```bash
cd project && git add dipworkpy/geography/map/inline.py tests/test_inline_map.py
git commit -m "$(cat <<'EOF'
feat(geography): implement InlineMap

Builds MapProtocol surface from an in-memory MapDefinition. Used by DDL
test fixtures and custom map variants passed inline in the request.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P2.5: Implement Map Registry + `fields_to_json` converter

**Files:**
- Create: `project/dipworkpy/geography/map/registry.py`
- Create: `project/dipworkpy/tools/__init__.py`
- Create: `project/dipworkpy/tools/fields_to_json.py`
- Test: `project/tests/test_map_registry.py`

- [x] **Step 1: Write failing test**

Create `project/tests/test_map_registry.py`:

```python
import pytest
from dipworkpy.geography.map.registry import get_map, list_maps, register_map


def test_get_standard_map():
    m = get_map("standard")
    assert m.map_id == "standard"
    assert m.field_exists("Vie")


def test_unknown_map_raises():
    with pytest.raises(KeyError):
        get_map("nonsuch")


def test_list_maps_contains_standard():
    assert "standard" in list_maps()


def test_register_custom_map():
    from dipworkpy.geo_model import MapDefinition
    from dipworkpy.geography.map.inline import InlineMap
    custom = InlineMap(MapDefinition(), map_id="empty_test")
    register_map(custom)
    assert "empty_test" in list_maps()
    assert get_map("empty_test").map_id == "empty_test"
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_map_registry.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement registry**

Create `project/dipworkpy/geography/map/registry.py`:

```python
"""Map registry - look up maps by id, register custom ones."""
from __future__ import annotations

from typing import Dict, List

from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.geography.map.standard import StandardMap

_registry: Dict[str, MapProtocol] = {}


def _bootstrap() -> None:
    if "standard" not in _registry:
        _registry["standard"] = StandardMap()


def get_map(map_id: str) -> MapProtocol:
    _bootstrap()
    if map_id not in _registry:
        raise KeyError(f"unknown map_id: {map_id!r}")
    return _registry[map_id]


def register_map(m: MapProtocol) -> None:
    _bootstrap()
    _registry[m.map_id] = m


def list_maps() -> List[str]:
    _bootstrap()
    return sorted(_registry.keys())
```

- [x] **Step 4: Implement `fields_to_json` converter (stub for now)**

Create `project/dipworkpy/tools/__init__.py` (empty) and `project/dipworkpy/tools/fields_to_json.py`:

```python
"""Convert a FIELDS-spec text file to the canonical standard.json schema.

CLI usage:
    python -m dipworkpy.tools.fields_to_json input.txt output.json

The FIELDS-spec format is line-based; each non-comment line is either a
field definition or an edge. Format (loosely):
    # <name> <x> <y> <sub_of-or-dash> <type> <sp> <home>
    - <from> <to> <army> <fleet> <convoy>

This converter is intentionally minimal: it does *not* know the legacy
private formats and may need extending. Use it as a starting point.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def parse_fields_text(text: str) -> Dict[str, Any]:
    fields: Dict[str, dict] = {}
    edges: Dict[str, dict] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        if line.startswith("#"):
            parts = line[1:].split()
            if len(parts) < 5:
                continue
            name, x, y, sub_of, ftype = parts[0], parts[1], parts[2], parts[3], parts[4]
            field: Dict[str, Any] = {"type": ftype, "pos": [int(x), int(y)]}
            if sub_of and sub_of != "-":
                field["sub_of"] = sub_of
            if len(parts) >= 6 and parts[5] == "1":
                field["is_supply_center"] = True
            if len(parts) >= 7:
                field["home_of"] = parts[6]
            fields[name] = field
        elif line.startswith("-"):
            parts = line[1:].split()
            if len(parts) < 5:
                continue
            frm, to, army, fleet, convoy = parts[0], parts[1], parts[2], parts[3], parts[4]
            edges[f"{frm}:{to}"] = {"army": army, "fleet": fleet, "convoy_move": convoy}
    return {"map_id": "standard", "fields": fields, "edges": edges}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    raw = args.input.read_text()
    data = parse_fields_text(raw)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True))
    print(f"wrote {len(data['fields'])} fields, {len(data['edges'])} edges to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 5: Run registry tests + lint**

Run: `cd project && poetry run python -m pytest tests/test_map_registry.py -v && poetry run ruff check dipworkpy/geography/map/registry.py dipworkpy/tools/ tests/test_map_registry.py && poetry run mypy dipworkpy/geography/map/registry.py`
Expected: 4 tests pass, lint clean.

- [x] **Step 6: Commit**

```bash
cd project && git add dipworkpy/geography/map/registry.py dipworkpy/tools/ tests/test_map_registry.py
git commit -m "$(cat <<'EOF'
feat(geography): map registry + fields_to_json converter

Registry resolves MapRef.map_id at service-call time. The converter ingests
the legacy FIELDS-spec text format and emits the canonical JSON.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P2.6: Resolve `MapRef` to `MapProtocol` instance

**Files:**
- Modify: `project/dipworkpy/geo_model.py` — add helper, OR
- Create: `project/dipworkpy/geography/map/resolve.py`
- Test: `project/tests/test_map_resolve.py`

- [x] **Step 1: Write failing test**

Create `project/tests/test_map_resolve.py`:

```python
from dipworkpy.geo_model import (
    Edge, FieldDef, FieldType, MapDefinition, MapRef, Passable,
)
from dipworkpy.geography.map.resolve import resolve_map_ref


def test_resolve_default_returns_standard():
    m = resolve_map_ref(MapRef())
    assert m.map_id == "standard"


def test_resolve_by_id():
    m = resolve_map_ref(MapRef(map_id="standard"))
    assert m.map_id == "standard"


def test_inline_wins_over_id():
    inline = MapDefinition(fields={"X": FieldDef(name="X", type=FieldType.L)}, edges={})
    m = resolve_map_ref(MapRef(map_id="standard", inline_map=inline))
    assert m.map_id == "inline"
    assert m.field_exists("X")
    assert not m.field_exists("Vie")
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_map_resolve.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement resolver**

Create `project/dipworkpy/geography/map/resolve.py`:

```python
"""Resolve a MapRef into a concrete MapProtocol instance."""
from __future__ import annotations

from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.inline import InlineMap
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.geography.map.registry import get_map


def resolve_map_ref(ref: MapRef) -> MapProtocol:
    """Inline wins; otherwise look up by map_id (default 'standard')."""
    if ref.inline_map is not None:
        return InlineMap(ref.inline_map)
    return get_map(ref.map_id or "standard")
```

- [x] **Step 4: Run tests + commit**

Run: `cd project && poetry run python -m pytest tests/test_map_resolve.py -v`
Expected: 3 tests pass.

```bash
cd project && git add dipworkpy/geography/map/resolve.py tests/test_map_resolve.py
git commit -m "$(cat <<'EOF'
feat(geography): resolve_map_ref helper

Single function bridging MapRef DTO to MapProtocol instance, with the
documented "inline wins over map_id" semantics.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase P1: DDL Renderer

Parallel to P2. Builds the DDL parser, the `Situation`/`InlineMap` converters, the matplotlib renderer, and the first 5 smoke examples.

### Task P1.1: DDL AST model

**Files:**
- Create: `project/dipworkpy/tools/dwex/__init__.py` (empty)
- Create: `project/dipworkpy/tools/dwex/model.py`
- Test: `project/tests/test_dwex_model.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_dwex_model.py`:

```python
from dipworkpy.tools.dwex.model import (
    DwexDocument, DwexField, DwexEdge, DwexUnit, DwexOrderSpec,
)


def test_minimal_document():
    doc = DwexDocument(
        title="t", description="",
        fields=[DwexField(name="A", type="LA", x=0, y=0)],
        edges=[],
        units=[],
        orders=[],
    )
    assert doc.title == "t"


def test_edge_default_passability():
    e = DwexEdge(a="A", b="B")
    assert e.army == "ja"
    assert e.fleet == "ja"
    assert e.convoy_move == "ja"


def test_edge_army_only():
    e = DwexEdge(a="A", b="B", army="ja", fleet="nein", convoy_move="nein")
    assert e.fleet == "nein"


def test_order_spec_failure_marker():
    o = DwexOrderSpec(
        nation="Au", utype="A", current="Vie", order="mve", dest="Tyr",
        expected_failed=True,
    )
    assert o.expected_failed is True
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_dwex_model.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement DDL model**

Create `project/dipworkpy/tools/dwex/model.py`:

```python
"""DDL AST - the parsed shape of a .dwex file."""
from __future__ import annotations

from typing import List, Literal, Optional, Set

from pydantic import BaseModel, Field

PassableStr = Literal["ja", "nein", "-", "imp"]


class DwexField(BaseModel):
    name: str
    type: str
    x: float
    y: float
    sub_of: Optional[str] = None


class DwexEdge(BaseModel):
    a: str
    b: str
    army: str = "ja"
    fleet: str = "ja"
    convoy_move: str = "ja"
    directed: bool = False


class DwexUnit(BaseModel):
    nation: str
    utype: str
    current: str


class DwexOrderSpec(BaseModel):
    nation: str
    utype: str
    current: str
    order: str  # hld, mve, hsup, msup, con
    dest: Optional[str] = None
    expected_failed: bool = False
    expected_dislodged: bool = False


class DwexDocument(BaseModel):
    title: str
    description: str = ""
    fields: List[DwexField] = Field(default_factory=list)
    edges: List[DwexEdge] = Field(default_factory=list)
    units: List[DwexUnit] = Field(default_factory=list)
    orders: List[DwexOrderSpec] = Field(default_factory=list)
    switches: dict = Field(default_factory=dict)
    expected_pattfields: Set[str] = Field(default_factory=set)
    note: str = ""
```

- [x] **Step 4: Run tests + commit**

Run: `cd project && poetry run python -m pytest tests/test_dwex_model.py -v && poetry run ruff check dipworkpy/tools/dwex/`
Expected: 4 tests pass, lint clean.

```bash
cd project && git add dipworkpy/tools/dwex/ tests/test_dwex_model.py
git commit -m "$(cat <<'EOF'
feat(dwex): DDL AST model

Pydantic shapes for parsed .dwex documents: fields, edges, units, orders
with optional result markers (! failed, > dislodged).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P1.2: DDL Parser

**Files:**
- Create: `project/dipworkpy/tools/dwex/lang.py`
- Test: `project/tests/test_dwex_lang.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_dwex_lang.py`:

```python
import pytest
from dipworkpy.tools.dwex.lang import parse, DwexParseError

EXAMPLE = """
@dwex
title: Two armies bouncing
desc: Equal strength bounce.

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
"""


def test_parses_title():
    doc = parse(EXAMPLE)
    assert doc.title == "Two armies bouncing"


def test_parses_description():
    doc = parse(EXAMPLE)
    assert "Equal" in doc.description


def test_parses_three_fields():
    doc = parse(EXAMPLE)
    names = {f.name for f in doc.fields}
    assert names == {"Vie", "Mun", "Tyr"}


def test_parses_field_positions():
    doc = parse(EXAMPLE)
    vie = next(f for f in doc.fields if f.name == "Vie")
    assert vie.x == 0.0
    assert vie.y == 0.0
    assert vie.type == "LA"


def test_parses_three_undirected_edges():
    doc = parse(EXAMPLE)
    pairs = {tuple(sorted([e.a, e.b])) for e in doc.edges}
    assert pairs == {("Mun", "Vie"), ("Tyr", "Vie"), ("Mun", "Tyr")}


def test_parses_orders_with_failure_marker():
    doc = parse(EXAMPLE)
    assert len(doc.orders) == 2
    for o in doc.orders:
        assert o.expected_failed is True


def test_extracts_units_from_orders():
    doc = parse(EXAMPLE)
    nations = {u.nation for u in doc.units}
    assert nations == {"Au", "Ge"}


def test_rejects_missing_dwex_marker():
    with pytest.raises(DwexParseError):
        parse("title: missing markers\nmap {}\norders {}")


def test_edge_modifier_army_only():
    text = """
@dwex
title: t
map {
  A LA 0,0
  B LA 1,0
  A --A B
}
@end
"""
    doc = parse(text)
    e = doc.edges[0]
    assert e.army == "ja"
    assert e.fleet == "nein"


def test_edge_modifier_fleet_only():
    text = """
@dwex
title: t
map {
  A O 0,0
  B O 1,0
  A --F B
}
@end
"""
    doc = parse(text)
    e = doc.edges[0]
    assert e.fleet == "ja"
    assert e.army == "nein"
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_dwex_lang.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement parser**

Create `project/dipworkpy/tools/dwex/lang.py`:

```python
"""DDL parser - line-based, block-oriented.

Grammar (loose):
    @dwex
    title: ...
    desc:  ...
    map { <field-lines> <edge-lines> }
    orders { <order-lines> }
    pattfields { <names> }
    note { ... }
    @end
"""
from __future__ import annotations

import re
from typing import List, Tuple

from dipworkpy.tools.dwex.model import (
    DwexDocument, DwexEdge, DwexField, DwexOrderSpec, DwexUnit,
)


class DwexParseError(ValueError):
    """Raised when the .dwex source fails to parse."""


_FIELD_RE = re.compile(r"^(\w+)\s+(\w+)\s+(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$")
_EDGE_RE = re.compile(r"^(\w+)\s+--([A-Z]*)\s+(\w+)$")
_ORDER_RE = re.compile(
    r"^(\w+)\s+(\w)\s+(\w+)\s+(hld|mve|hsup|msup|con)(?:\s+(\w+))?\s*([!>]*)$"
)


def _strip_inline_comment(line: str) -> str:
    return re.sub(r"\s+#.*$", "", line).strip()


def _passability_for_modifier(mod: str) -> Tuple[str, str, str]:
    """Translate edge modifier suffix into (army, fleet, convoy_move) values."""
    mod = mod.upper()
    if mod == "" or mod == "AF":
        return ("ja", "ja", "ja")
    if mod == "A":
        return ("ja", "nein", "nein")
    if mod == "F":
        return ("nein", "ja", "ja")
    if mod == "C":
        return ("nein", "nein", "ja")
    raise DwexParseError(f"unknown edge modifier: --{mod}")


def _extract_block(text: str, block: str) -> str:
    pat = re.compile(rf"{block}\s*\{{(.*?)\}}", re.DOTALL)
    m = pat.search(text)
    return m.group(1) if m else ""


def parse(text: str) -> DwexDocument:
    if "@dwex" not in text or "@end" not in text:
        raise DwexParseError("missing @dwex / @end markers")

    lines = [_strip_inline_comment(ln) for ln in text.splitlines()]
    joined = "\n".join(lines)

    title_m = re.search(r"^title:\s*(.+)$", joined, re.MULTILINE)
    if not title_m:
        raise DwexParseError("missing title:")
    title = title_m.group(1).strip()

    desc_m = re.search(r"^desc:\s*(.+)$", joined, re.MULTILINE)
    description = desc_m.group(1).strip() if desc_m else ""

    fields: List[DwexField] = []
    edges: List[DwexEdge] = []
    map_body = _extract_block(joined, "map")
    for raw in map_body.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        fm = _FIELD_RE.match(ln)
        em = _EDGE_RE.match(ln)
        if fm:
            fields.append(DwexField(
                name=fm.group(1), type=fm.group(2),
                x=float(fm.group(3)), y=float(fm.group(4)),
            ))
        elif em:
            a, mod, b = em.group(1), em.group(2), em.group(3)
            army, fleet, conv = _passability_for_modifier(mod)
            edges.append(DwexEdge(a=a, b=b, army=army, fleet=fleet, convoy_move=conv))
        else:
            raise DwexParseError(f"unparsable map line: {ln!r}")

    orders: List[DwexOrderSpec] = []
    orders_body = _extract_block(joined, "orders")
    for raw in orders_body.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        om = _ORDER_RE.match(ln)
        if not om:
            raise DwexParseError(f"unparsable order line: {ln!r}")
        nat, utype, current, order, dest, marks = om.groups()
        orders.append(DwexOrderSpec(
            nation=nat, utype=utype, current=current,
            order=order, dest=dest,
            expected_failed=("!" in (marks or "")),
            expected_dislodged=(">" in (marks or "")),
        ))

    units = [DwexUnit(nation=o.nation, utype=o.utype, current=o.current) for o in orders]

    return DwexDocument(
        title=title, description=description,
        fields=fields, edges=edges, units=units, orders=orders,
    )


def parse_file(path) -> DwexDocument:
    from pathlib import Path
    return parse(Path(path).read_text())
```

- [x] **Step 4: Run tests + commit**

Run: `cd project && poetry run python -m pytest tests/test_dwex_lang.py -v && poetry run ruff check dipworkpy/tools/dwex/lang.py`
Expected: 10 tests pass.

```bash
cd project && git add dipworkpy/tools/dwex/lang.py tests/test_dwex_lang.py
git commit -m "$(cat <<'EOF'
feat(dwex): DDL parser

Block-oriented line parser. Edge modifier --A/--F/--C/--AF translates to
the three Passable values. Failure/dislodge markers in order lines
captured as expected_failed / expected_dislodged on the AST.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P1.3: DDL → Situation + InlineMap converters

**Files:**
- Create: `project/dipworkpy/tools/dwex/to_situation.py`
- Create: `project/dipworkpy/tools/dwex/to_map.py`
- Test: `project/tests/test_dwex_converters.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_dwex_converters.py`:

```python
from dipworkpy.tools.dwex.lang import parse
from dipworkpy.tools.dwex.to_situation import to_situation, to_expected
from dipworkpy.tools.dwex.to_map import to_inline_map
from dipworkpy.model import OrderType

DOC = """
@dwex
title: t
map {
  Vie LA 0,0
  Mun LA 1,0
  Tyr L  0,1
  Vie -- Mun
  Vie -- Tyr
  Mun -- Tyr
}
orders {
  Au A Vie mve Tyr !
  Ge A Mun mve Tyr !
}
@end
"""


def test_to_situation_produces_orders():
    doc = parse(DOC)
    sit = to_situation(doc)
    assert len(sit.orders) == 2
    assert sit.orders[0].nation == "Au"
    assert sit.orders[0].order == OrderType.mve
    assert sit.orders[0].dest == "Tyr"


def test_to_expected_marks_failures():
    doc = parse(DOC)
    exp = to_expected(doc)
    assert all(r.succeeds is False for r in exp.orders)


def test_to_inline_map_has_three_fields():
    doc = parse(DOC)
    m = to_inline_map(doc)
    assert m.field_exists("Vie")
    assert m.field_exists("Mun")
    assert m.field_exists("Tyr")


def test_to_inline_map_has_six_directed_edges():
    doc = parse(DOC)
    m = to_inline_map(doc)
    # 3 undirected edges -> 6 directed
    assert m.edge("Vie", "Mun") is not None
    assert m.edge("Mun", "Vie") is not None
    assert m.edge("Vie", "Tyr") is not None
    assert m.edge("Tyr", "Vie") is not None
```

- [x] **Step 2: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_dwex_converters.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 3: Implement converters**

Create `project/dipworkpy/tools/dwex/to_situation.py`:

```python
"""DDL -> Situation / expected ConflictResolution."""
from __future__ import annotations

from dipworkpy.model import (
    ConflictResolution, Order, OrderResult, OrderType, Situation,
)
from dipworkpy.tools.dwex.model import DwexDocument


def to_situation(doc: DwexDocument) -> Situation:
    orders = []
    for o in doc.orders:
        orders.append(Order(
            nation=o.nation, utype=o.utype, current=o.current,
            order=OrderType(o.order), dest=o.dest,
        ))
    return Situation(orders=orders)


def to_expected(doc: DwexDocument) -> ConflictResolution:
    results = []
    for o in doc.orders:
        results.append(OrderResult(
            nation=o.nation, utype=o.utype, current=o.current,
            order=OrderType(o.order), dest=o.dest,
            succeeds=False if o.expected_failed else None,
            dislodged=True if o.expected_dislodged else None,
        ))
    return ConflictResolution(orders=results, pattfields=doc.expected_pattfields)
```

Create `project/dipworkpy/tools/dwex/to_map.py`:

```python
"""DDL -> InlineMap."""
from __future__ import annotations

from dipworkpy.geo_model import (
    Edge, FieldDef, FieldType, MapDefinition, Passable,
)
from dipworkpy.geography.map.inline import InlineMap
from dipworkpy.tools.dwex.model import DwexDocument


def _pass(val: str):
    try:
        return Passable(val)
    except ValueError:
        # could be a subfield name (coast-required); pass through as str
        return val


def to_inline_map(doc: DwexDocument) -> InlineMap:
    fields = {}
    for f in doc.fields:
        fields[f.name] = FieldDef(
            name=f.name, type=FieldType(f.type),
            sub_of=f.sub_of, pos=(f.x, f.y),
        )
    edges = {}
    for e in doc.edges:
        ed = Edge(army=_pass(e.army), fleet=_pass(e.fleet),
                  convoy_move=_pass(e.convoy_move))
        edges[(e.a, e.b)] = ed
        if not e.directed:
            edges[(e.b, e.a)] = ed
    return InlineMap(MapDefinition(fields=fields, edges=edges), map_id="dwex_inline")
```

- [x] **Step 4: Run tests + commit**

Run: `cd project && poetry run python -m pytest tests/test_dwex_converters.py -v`
Expected: 4 tests pass.

```bash
cd project && git add dipworkpy/tools/dwex/to_situation.py dipworkpy/tools/dwex/to_map.py tests/test_dwex_converters.py
git commit -m "$(cat <<'EOF'
feat(dwex): DDL -> Situation / InlineMap converters

Closes the loop: a parsed .dwex document yields an executable Situation
(for conflict_game) plus an InlineMap (for geography_phase) plus the
expected ConflictResolution (for assertions). One source, three artifacts.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P1.4: DDL Renderer (matplotlib)

**Files:**
- Create: `project/dipworkpy/tools/dwex/render_png.py`
- Test: `project/tests/test_dwex_render.py`
- Modify: `project/pyproject.toml` — add matplotlib to deps

- [x] **Step 1: Add matplotlib dependency**

Modify `project/pyproject.toml`. Inside `[tool.poetry.dependencies]`, after `pydantic`, add:

```toml
matplotlib = "^3.7"
```

Run: `cd project && poetry lock --no-update && poetry install`
Expected: matplotlib installed.

- [x] **Step 2: Write failing test**

Create `project/tests/test_dwex_render.py`:

```python
from pathlib import Path
from dipworkpy.tools.dwex.lang import parse
from dipworkpy.tools.dwex.render_png import render_png

DOC = """
@dwex
title: Smoke test
map {
  A LA 0,0
  B LA 1,0
  A -- B
}
orders {
  Au A A mve B
}
@end
"""


def test_render_writes_png(tmp_path: Path):
    doc = parse(DOC)
    out = tmp_path / "smoke.png"
    render_png(doc, out)
    assert out.exists()
    assert out.stat().st_size > 1000  # non-trivial PNG
    # PNG magic bytes
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
```

- [x] **Step 3: Verify failure**

Run: `cd project && poetry run python -m pytest tests/test_dwex_render.py -v`
Expected: ModuleNotFoundError.

- [x] **Step 4: Implement renderer**

Create `project/dipworkpy/tools/dwex/render_png.py`:

```python
"""DDL -> PNG via matplotlib."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

from dipworkpy.tools.dwex.model import DwexDocument


NATION_COLORS: Dict[str, str] = {
    "Au": "#E84545", "En": "#3A5BA0", "Fr": "#79B8E0", "Ge": "#444444",
    "It": "#3DA34D", "Ru": "#E0E0E0", "Tu": "#F2C94C", "Xx": "#888888",
}

FIELD_COLORS = {
    "LA": "#E8D9B5", "L": "#D6E8B5", "LCB": "#E8E0B5", "LC": "#E8E0B5",
    "LCA": "#E8E0B5", "LCF": "#E8E0B5", "O": "#B5D6E8", "COL": "#CCCCCC",
}


def render_png(doc: DwexDocument, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 7), dpi=100)

    pos = {f.name: (f.x, f.y) for f in doc.fields}

    # edges
    for e in doc.edges:
        if e.a not in pos or e.b not in pos:
            continue
        x1, y1 = pos[e.a]
        x2, y2 = pos[e.b]
        color = "gray"
        if e.army == "ja" and e.fleet == "nein":
            color = "#5b8c5a"
        elif e.fleet == "ja" and e.army == "nein":
            color = "#3a6ea5"
        ax.plot([x1, x2], [y1, y2], color=color, lw=1.3, zorder=1)

    # fields
    radius = 0.22
    for f in doc.fields:
        x, y = f.x, f.y
        fc = FIELD_COLORS.get(f.type, "#FFFFFF")
        ax.add_patch(Circle((x, y), radius, facecolor=fc, edgecolor="black",
                            lw=1.2, zorder=2))
        ax.text(x, y - radius - 0.08, f.name, ha="center", va="top",
                fontsize=10, weight="bold", zorder=3)

    # units (drawn at field pos with small offset)
    for u in doc.units:
        if u.current not in pos:
            continue
        x, y = pos[u.current]
        color = NATION_COLORS.get(u.nation, "#888888")
        ax.text(x, y, f"{u.utype}:{u.nation}", ha="center", va="center",
                fontsize=9, color="white",
                bbox=dict(boxstyle="round,pad=0.2", facecolor=color, edgecolor="none"),
                zorder=4)

    # order arrows
    for o in doc.orders:
        if o.order != "mve" or o.dest not in pos or o.current not in pos:
            continue
        x1, y1 = pos[o.current]
        x2, y2 = pos[o.dest]
        color = "red" if o.expected_failed else "#2e7d32"
        style = "dashed" if o.expected_failed else "solid"
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="->", mutation_scale=14, color=color,
            linestyle=style, lw=1.6, shrinkA=18, shrinkB=18, zorder=5,
        )
        ax.add_patch(arrow)

    # title
    ax.set_title(doc.title, fontsize=12)

    # styling
    xs = [f.x for f in doc.fields]
    ys = [f.y for f in doc.fields]
    if xs and ys:
        pad = 0.6
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.set_axis_off()

    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
```

- [x] **Step 5: Run tests + commit**

Run: `cd project && poetry run python -m pytest tests/test_dwex_render.py -v`
Expected: 1 test passes.

```bash
cd project && git add dipworkpy/tools/dwex/render_png.py tests/test_dwex_render.py pyproject.toml poetry.lock
git commit -m "$(cat <<'EOF'
feat(dwex): matplotlib renderer

Produces a PNG visualization from a DwexDocument: fields as type-colored
circles, units as nation-colored badges, mve orders as green/red arrows.
Pure Python (matplotlib only), no system graphviz needed.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P1.5: DDL CLI + 5 smoke examples

**Files:**
- Create: `project/dipworkpy/tools/dwex/cli.py`
- Create: `project/dipworkpy/tools/dwex/__main__.py`
- Create: `project/doc/examples/README.md`
- Create: `project/doc/examples/dwex/01_basic_hold.dwex`
- Create: `project/doc/examples/dwex/02_simple_move.dwex`
- Create: `project/doc/examples/dwex/03_equal_bounce.dwex`
- Create: `project/doc/examples/dwex/04_support_hold.dwex`
- Create: `project/doc/examples/dwex/05_support_move.dwex`

- [x] **Step 1: Implement CLI**

Create `project/dipworkpy/tools/dwex/cli.py`:

```python
"""DDL CLI: render, render-all, validate, to-json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dipworkpy.tools.dwex.lang import parse_file
from dipworkpy.tools.dwex.render_png import render_png
from dipworkpy.tools.dwex.to_situation import to_situation, to_expected


def cmd_render(args: argparse.Namespace) -> int:
    doc = parse_file(args.path)
    out = args.path.with_suffix(".png")
    render_png(doc, out)
    print(f"rendered {out}")
    return 0


def cmd_render_all(args: argparse.Namespace) -> int:
    count = 0
    for p in sorted(args.dir.rglob("*.dwex")):
        doc = parse_file(p)
        out = p.with_suffix(".png")
        render_png(doc, out)
        print(f"rendered {out}")
        count += 1
    print(f"{count} files rendered")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from dipworkpy.conflict_game import conflict_game
    doc = parse_file(args.path)
    sit = to_situation(doc)
    expected = to_expected(doc)
    result = conflict_game(sit)
    ok = result <= expected
    print(f"{'PASS' if ok else 'FAIL'} {args.path}")
    return 0 if ok else 1


def cmd_to_json(args: argparse.Namespace) -> int:
    doc = parse_file(args.path)
    sit = to_situation(doc)
    print(sit.model_dump_json(indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser("dwex")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render"); r.add_argument("path", type=Path); r.set_defaults(fn=cmd_render)
    a = sub.add_parser("render-all"); a.add_argument("dir", type=Path); a.set_defaults(fn=cmd_render_all)
    v = sub.add_parser("validate"); v.add_argument("path", type=Path); v.set_defaults(fn=cmd_validate)
    j = sub.add_parser("to-json"); j.add_argument("path", type=Path); j.set_defaults(fn=cmd_to_json)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
```

Create `project/dipworkpy/tools/dwex/__main__.py`:

```python
from dipworkpy.tools.dwex.cli import main
import sys
sys.exit(main())
```

- [x] **Step 2: Create 5 smoke examples**

Create `project/doc/examples/dwex/01_basic_hold.dwex`:

```
@dwex
title: 01 — Basic Hold
desc:  Single unit holding. Trivial baseline.

map {
  Vie LA 0,0
}

orders {
  Au A Vie hld
}
@end
```

Create `project/doc/examples/dwex/02_simple_move.dwex`:

```
@dwex
title: 02 — Simple Move
desc:  Single unit moves to adjacent empty field.

map {
  Vie LA 0,0
  Tyr L  1,0
  Vie -- Tyr
}

orders {
  Au A Vie mve Tyr
}
@end
```

Create `project/doc/examples/dwex/03_equal_bounce.dwex`:

```
@dwex
title: 03 — Equal Bounce
desc:  Two armies of equal strength move to same field. Both bounce.

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

Create `project/doc/examples/dwex/04_support_hold.dwex`:

```
@dwex
title: 04 — Support Hold
desc:  A hold-support fends off an equal attacker.

map {
  Vie LA 0,0
  Mun LA 2,0
  Tyr L  1,0
  Boh L  -1,0
  Boh -- Vie
  Vie -- Tyr
  Vie -- Mun
  Mun -- Tyr
}

orders {
  Au A Vie hld
  Au A Boh hsup Vie
  Ge A Mun mve Vie !
}
@end
```

Create `project/doc/examples/dwex/05_support_move.dwex`:

```
@dwex
title: 05 — Support Move
desc:  A move-support tips the balance over an equal defender.

map {
  Vie LA 0,0
  Mun LA 2,0
  Boh L  1,1
  Vie -- Mun
  Boh -- Mun
}

orders {
  Au A Vie mve Mun
  Au A Boh msup Vie
  Ge A Mun hld >
}
@end
```

- [x] **Step 3: Render the smoke examples**

Run: `cd project && poetry run python -m dipworkpy.tools.dwex render-all doc/examples/dwex`
Expected: 5 PNGs created.

- [x] **Step 4: Validate them against conflict_game**

Run: `cd project && for f in doc/examples/dwex/*.dwex; do poetry run python -m dipworkpy.tools.dwex validate "$f"; done`
Expected: 5 PASS lines.

- [x] **Step 5: Create README**

Create `project/doc/examples/README.md`:

```markdown
# DDL Examples

Each `.dwex` file is parsed by `dipworkpy.tools.dwex.lang.parse()` and
produces:
- a sibling `.png` (visualization)
- a `Situation` for `conflict_game()`
- a `ConflictResolution` to assert against (driven by `!`/`>` markers)

## Render / validate

    poetry run python -m dipworkpy.tools.dwex render-all doc/examples/dwex
    poetry run python -m dipworkpy.tools.dwex validate doc/examples/dwex/01_basic_hold.dwex

## Language reference

See `docs/superpowers/specs/2026-05-12-dipworkpy-comprehensive-design.md`
section 6.
```

- [x] **Step 6: Commit**

```bash
cd project && git add dipworkpy/tools/dwex/cli.py dipworkpy/tools/dwex/__main__.py doc/examples/
git commit -m "$(cat <<'EOF'
feat(dwex): CLI + 5 smoke examples + rendered PNGs

01-05 cover hold, move, bounce, support-hold, support-move. PNGs committed
so GitHub renders them inline; CI verifies they stay in sync.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P1.6: Parametrized DDL test (every .dwex is a regression test)

**Files:**
- Create: `project/tests/test_dwex_examples.py`

- [x] **Step 1: Write the parametrized test**

Create `project/tests/test_dwex_examples.py`:

```python
"""Every .dwex example is automatically a regression test for conflict_game."""
from pathlib import Path

import pytest

from dipworkpy.conflict_game import conflict_game
from dipworkpy.tools.dwex.lang import parse_file
from dipworkpy.tools.dwex.to_situation import to_expected, to_situation

DWEX_ROOT = Path(__file__).resolve().parent.parent / "doc/examples/dwex"


def _ids(p: Path) -> str:
    return p.stem


@pytest.mark.parametrize(
    "path",
    sorted(DWEX_ROOT.rglob("*.dwex")),
    ids=_ids,
)
def test_dwex_example_runs_clean(path: Path) -> None:
    doc = parse_file(path)
    sit = to_situation(doc)
    expected = to_expected(doc)
    result = conflict_game(sit)
    assert result <= expected, (
        f"{path.stem}: result mismatch\n"
        f"expected: {expected.__log__()}\n"
        f"actual:   {result.__log__()}"
    )
```

- [x] **Step 2: Run it**

Run: `cd project && poetry run python -m pytest tests/test_dwex_examples.py -v`
Expected: 5 PASS (one per smoke example).

- [x] **Step 3: Commit**

```bash
cd project && git add tests/test_dwex_examples.py
git commit -m "$(cat <<'EOF'
test(dwex): parametrized regression test over every .dwex example

Each .dwex file is loaded, executed through conflict_game, and the result
asserted against the expected_failed / expected_dislodged markers in the
DDL source. Adding a new example means adding a new test, automatically.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase P3: Geography Service

Needs P2 complete. Implements the order-classifier per Gilgamesch B.2.6.1, ConvoyGraph extraction, and the `geography_phase` entry point.

### Task P3.1: Geography request/response models

**Files:**
- Create: `project/dipworkpy/geography/model.py`
- Test: `project/tests/test_geography_model.py`

- [x] **Step 1: Write failing test**

Create `project/tests/test_geography_model.py`:

```python
from dipworkpy.geo_model import MapRef
from dipworkpy.geography.model import GeographyRequest, GeographyResponse
from dipworkpy.model import Order, OrderType


def test_geography_request_defaults():
    req = GeographyRequest(orders=[])
    assert req.map.map_id == "standard"


def test_geography_request_with_orders():
    orders = [Order(nation="Au", utype="A", current="Vie", order=OrderType.hld)]
    req = GeographyRequest(orders=orders)
    assert len(req.orders) == 1


def test_geography_response_default_empty():
    resp = GeographyResponse(orders=[], order_geo_info=[])
    assert resp.convoy_graph.sea_edges == set()
    assert resp.diagnostics == []
```

- [x] **Step 2: Verify failure, then implement**

Run: `cd project && poetry run python -m pytest tests/test_geography_model.py -v`
Expected: ModuleNotFoundError.

Create `project/dipworkpy/geography/model.py`:

```python
"""Geography-service request/response DTOs."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import ConvoyGraph, MapRef, OrderGeoInfo
from dipworkpy.model import Order


class GeographyRequest(BaseModel):
    orders: List[Order]
    map: MapRef = Field(default_factory=MapRef)


class GeographyResponse(BaseModel):
    orders: List[Order]
    order_geo_info: List[OrderGeoInfo] = Field(default_factory=list)
    convoy_graph: ConvoyGraph = Field(default_factory=ConvoyGraph)
    diagnostics: List[Diagnostic] = Field(default_factory=list)
```

- [x] **Step 3: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_geography_model.py -v`
Expected: 3 pass.

```bash
cd project && git add dipworkpy/geography/model.py tests/test_geography_model.py
git commit -m "feat(geography): request/response DTOs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P3.2: GEO-001..003 — move-validity rules

**Files:**
- Create: `project/dipworkpy/geography/rules.py`
- Test: `project/tests/test_geo_rules_move.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_geo_rules_move.py`:

```python
from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.rules import classify_move
from dipworkpy.model import Order, OrderType


def _o(current: str, dest: str) -> Order:
    return Order(nation="Au", utype="A", current=current,
                 order=OrderType.mve, dest=dest)


def test_geo_001_unknown_destination():
    m = resolve_map_ref(MapRef())
    info = classify_move(_o("Vie", "ZZZ"), m, order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-001"
    assert info.effective_behavior == "holds_no_support"


def test_geo_002_start_equals_destination():
    m = resolve_map_ref(MapRef())
    info = classify_move(_o("Vie", "Vie"), m, order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-002"
    assert info.effective_behavior == "holds_no_support"


def test_geo_003_not_reachable():
    m = resolve_map_ref(MapRef())
    info = classify_move(_o("Vie", "Lon"), m, order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-003"
    assert info.effective_behavior == "holds_no_support"


def test_valid_move_is_moves():
    m = resolve_map_ref(MapRef())
    info = classify_move(_o("Vie", "Boh"), m, order_index=0)
    assert info.is_valid is True
    assert info.effective_behavior == "moves"
```

- [x] **Step 2: Verify failure, then implement**

Create `project/dipworkpy/geography/rules.py`:

```python
"""Per-rule order classification (GEO-001 .. GEO-010)."""
from __future__ import annotations

from typing import List

from dipworkpy.geo_model import OrderGeoInfo
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order, OrderType


def classify_move(o: Order, m: MapProtocol, order_index: int) -> OrderGeoInfo:
    """Apply GEO-001..003 to a mve order."""
    if o.dest is None or not m.field_exists(o.dest):
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-001",
            invalidity_reason=f"destination {o.dest!r} not on map",
            effective_behavior="holds_no_support",
        )
    if o.dest == o.current:
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-002",
            invalidity_reason="start == destination",
            effective_behavior="holds_no_support",
        )
    # GEO-003: reachable? (direct neighbor — convoy chain check is in later rule)
    if o.dest not in m.neighbors(o.current):
        # not directly adjacent — could still be convoyable (handled by GEO-009)
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-003",
            invalidity_reason=f"{o.dest} not adjacent to {o.current} (no convoy detected)",
            effective_behavior="holds_no_support",
        )
    return OrderGeoInfo(
        order_index=order_index, is_valid=True,
        effective_behavior="moves",
    )
```

- [x] **Step 3: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_geo_rules_move.py -v`
Expected: 4 pass.

```bash
cd project && git add dipworkpy/geography/rules.py tests/test_geo_rules_move.py
git commit -m "feat(geography): GEO-001..003 move-validity rules

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P3.3: GEO-004 — support-reachability rule (B.3.1.1)

**Files:**
- Modify: `project/dipworkpy/geography/rules.py` — add `classify_support`
- Test: `project/tests/test_geo_rules_support.py`

- [x] **Step 1: Write failing test**

Create `project/tests/test_geo_rules_support.py`:

```python
from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.rules import classify_support
from dipworkpy.model import Order, OrderType


def _sup(current: str, dest: str, order=OrderType.hsup) -> Order:
    return Order(nation="Au", utype="A", current=current, order=order, dest=dest)


def test_valid_hold_support_direct_neighbor():
    m = resolve_map_ref(MapRef())
    # Boh supports Vie (direct neighbor)
    info = classify_support(_sup("Boh", "Vie"), m, supported_target="Vie", order_index=0)
    assert info.is_valid is True
    assert info.effective_behavior == "moves"


def test_invalid_support_unreachable():
    m = resolve_map_ref(MapRef())
    # Vie tries to support a unit in Lon — Lon is not adjacent to Vie
    info = classify_support(_sup("Vie", "Lon"), m, supported_target="Lon", order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-004"
    assert info.effective_behavior == "holds_supportable"
```

- [x] **Step 2: Implement**

Append to `project/dipworkpy/geography/rules.py`:

```python
def classify_support(o: Order, m: MapProtocol, *, supported_target: str,
                     order_index: int) -> OrderGeoInfo:
    """GEO-004: supporter must reach supported_target from a direct neighbor.

    Per Gilgamesch B.3.1.1: no convoy, no furt — strict direct adjacency.
    """
    if not m.field_exists(supported_target):
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=f"supported target {supported_target!r} unknown",
            effective_behavior="holds_supportable",
        )
    if supported_target not in m.neighbors(o.current):
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-004",
            invalidity_reason=f"{o.current} cannot reach {supported_target} directly",
            effective_behavior="holds_supportable",
        )
    return OrderGeoInfo(
        order_index=order_index, is_valid=True,
        effective_behavior="moves",
    )
```

- [x] **Step 3: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_geo_rules_support.py -v`
Expected: 2 pass.

```bash
cd project && git add dipworkpy/geography/rules.py tests/test_geo_rules_support.py
git commit -m "feat(geography): GEO-004 support-reachability rule (Gilgamesch B.3.1.1)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P3.4: GEO-005..006 — convoy preconditions

**Files:**
- Modify: `project/dipworkpy/geography/rules.py` — add `classify_convoy`
- Test: `project/tests/test_geo_rules_convoy.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_geo_rules_convoy.py`:

```python
from dipworkpy.geo_model import FieldType, MapRef
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.rules import classify_convoy
from dipworkpy.model import Order, OrderType


def _con(current: str, ref: str) -> Order:
    return Order(nation="En", utype="F", current=current, order=OrderType.con, dest=ref)


def test_geo_005_convoyer_not_on_sea():
    m = resolve_map_ref(MapRef())
    # Vie is land, not sea — invalid convoyer
    info = classify_convoy(_con("Vie", "Lon"), m, convoyed_dest="Bel", order_index=0)
    assert info.is_valid is False
    assert info.invalidity_code == "GEO-005"
    assert info.effective_behavior == "holds_supportable"


def test_geo_006_valid_convoyer_nth():
    m = resolve_map_ref(MapRef())
    # F NTH con A Lon mve Bel — NTH is sea, both Lon+Bel adjacent to NTH
    info = classify_convoy(_con("NTH", "Lon"), m, convoyed_dest="Bel", order_index=0)
    assert info.is_valid is True
```

- [x] **Step 2: Implement**

Append to `project/dipworkpy/geography/rules.py`:

```python
def classify_convoy(o: Order, m: MapProtocol, *, convoyed_dest: str,
                    order_index: int) -> OrderGeoInfo:
    """GEO-005/006 for convoy orders.

    - GEO-005: convoyer must be on a sea field.
    - GEO-006: convoyer must be adjacent to both the army's start (o.dest)
      and the army's destination.
    """
    from dipworkpy.geo_model import FieldType
    if not m.field_exists(o.current):
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-005",
            invalidity_reason=f"convoyer field {o.current!r} unknown",
            effective_behavior="holds_supportable",
        )
    if m.field_type(o.current) != FieldType.O:
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-005",
            invalidity_reason=f"{o.current} is not a sea field",
            effective_behavior="holds_supportable",
        )
    army_start = o.dest  # by DipworkPy convention, con.dest = army start field
    nbrs = m.neighbors(o.current)
    if army_start not in nbrs or convoyed_dest not in nbrs:
        return OrderGeoInfo(
            order_index=order_index, is_valid=False,
            invalidity_code="GEO-006",
            invalidity_reason=(
                f"convoyer {o.current} not adjacent to both "
                f"{army_start} and {convoyed_dest}"
            ),
            effective_behavior="holds_supportable",
        )
    return OrderGeoInfo(
        order_index=order_index, is_valid=True,
        effective_behavior="moves",
    )
```

- [x] **Step 3: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_geo_rules_convoy.py -v`
Expected: 2 pass.

```bash
cd project && git add dipworkpy/geography/rules.py tests/test_geo_rules_convoy.py
git commit -m "feat(geography): GEO-005/006 convoy preconditions

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P3.5: GEO-007..008 — subfield resolution & normalization

**Files:**
- Create: `project/dipworkpy/geography/coast.py`
- Test: `project/tests/test_geo_coast.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_geo_coast.py`:

```python
from dipworkpy.geo_model import MapRef
from dipworkpy.geography.coast import resolve_coast, normalize_to_superfield
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.model import Order, OrderType


def test_normalize_subfield_to_superfield():
    m = resolve_map_ref(MapRef())
    assert normalize_to_superfield("SpN", m) == "Spa"
    assert normalize_to_superfield("Spa", m) == "Spa"
    assert normalize_to_superfield("Vie", m) == "Vie"


def test_resolve_coast_deterministic():
    m = resolve_map_ref(MapRef())
    # F Spa mve MID — only SpS reaches MID
    o = Order(nation="Fr", utype="F", current="Spa", order=OrderType.mve, dest="MID")
    coast = resolve_coast(o, m)
    assert coast == "SpS"


def test_resolve_coast_none_for_unambiguous_field():
    m = resolve_map_ref(MapRef())
    # F Bre mve MID — no coast question
    o = Order(nation="Fr", utype="F", current="Bre", order=OrderType.mve, dest="MID")
    coast = resolve_coast(o, m)
    assert coast is None
```

- [x] **Step 2: Implement**

Create `project/dipworkpy/geography/coast.py`:

```python
"""Subfield (coast) resolution and superfield normalization.

GEO-007: when a fleet sits on a split-coast superfield (e.g. Spa) and the
move destination is reachable only from one coast, we resolve which.
GEO-008: outputs are always normalized to the superfield code; the
resolved coast travels in OrderGeoInfo.resolved_coast.
"""
from __future__ import annotations

from typing import Optional

from dipworkpy.geo_model import Passable
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order


def normalize_to_superfield(fld: str, m: MapProtocol) -> str:
    """SpN -> Spa, Vie -> Vie, Spa -> Spa."""
    if not m.field_exists(fld):
        return fld
    return m.superfield_of(fld)


def resolve_coast(o: Order, m: MapProtocol) -> Optional[str]:
    """If Fleet on a split-coast superfield, decide which coast based on dest."""
    if o.utype != "F" or o.dest is None:
        return None
    subs = m.subfields_of(o.current)
    if not subs:
        return None
    candidates = []
    for sub in subs:
        nbrs = m.neighbors(sub)
        if o.dest in nbrs:
            candidates.append(sub)
    if len(candidates) == 1:
        return candidates[0]
    return None
```

- [x] **Step 3: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_geo_coast.py -v`
Expected: 3 pass.

```bash
cd project && git add dipworkpy/geography/coast.py tests/test_geo_coast.py
git commit -m "feat(geography): GEO-007/008 coast resolution

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P3.6: GEO-009 — cmove classification & ConvoyGraph extraction

**Files:**
- Create: `project/dipworkpy/geography/convoy.py`
- Test: `project/tests/test_geo_convoy.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_geo_convoy.py`:

```python
from dipworkpy.geo_model import FieldType, MapRef
from dipworkpy.geography.convoy import build_convoy_graph, classify_cmove_candidates
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.model import Order, OrderType


def test_empty_graph_with_no_convoy_orders():
    m = resolve_map_ref(MapRef())
    orders = [Order(nation="Au", utype="A", current="Vie", order=OrderType.hld)]
    g = build_convoy_graph(orders, m)
    assert g.convoyer_fields == set()


def test_graph_includes_convoyer():
    m = resolve_map_ref(MapRef())
    orders = [
        Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="Bel"),
        Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Lon"),
    ]
    g = build_convoy_graph(orders, m)
    assert "NTH" in g.convoyer_fields
    assert 0 in g.cmove_candidates  # Lon->Bel classified as cmove


def test_classify_cmove_no_convoy_no_candidate():
    m = resolve_map_ref(MapRef())
    orders = [Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Tyr")]
    cmoves = classify_cmove_candidates(orders, m)
    assert cmoves == set()
```

- [x] **Step 2: Implement**

Create `project/dipworkpy/geography/convoy.py`:

```python
"""Convoy-graph extraction and cmove classification (GEO-009)."""
from __future__ import annotations

from typing import List, Set

from dipworkpy.geo_model import ConvoyGraph, FieldType, Passable
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order, OrderType


def _convoyer_fields(orders: List[Order]) -> Set[str]:
    return {o.current for o in orders if o.order == OrderType.con}


def classify_cmove_candidates(orders: List[Order], m: MapProtocol) -> Set[int]:
    """Indices of mve orders that have a matching con order keyed on current."""
    convoyed_starts: Set[str] = set()
    for o in orders:
        if o.order == OrderType.con and o.dest:
            convoyed_starts.add(o.dest)
    cmoves: Set[int] = set()
    for i, o in enumerate(orders):
        if o.order == OrderType.mve and o.current in convoyed_starts:
            cmoves.add(i)
    return cmoves


def build_convoy_graph(orders: List[Order], m: MapProtocol) -> ConvoyGraph:
    convoyers = _convoyer_fields(orders)
    sea_edges: Set[tuple] = set()
    coastal_edges: Set[tuple] = set()

    # Build sea-sea and sea-coast adjacencies relevant for convoy.
    for sea in convoyers:
        if not m.field_exists(sea) or m.field_type(sea) != FieldType.O:
            continue
        for nb in m.neighbors(sea):
            if not m.field_exists(nb):
                continue
            t = m.field_type(nb)
            if t == FieldType.O and nb in convoyers:
                sea_edges.add(tuple(sorted([sea, nb])))
            elif t in {FieldType.LCB, FieldType.LC, FieldType.LCA, FieldType.LCF}:
                coastal_edges.add((sea, nb))
                coastal_edges.add((nb, sea))

    return ConvoyGraph(
        sea_edges=sea_edges,
        coastal_edges=coastal_edges,
        convoyer_fields=convoyers,
        cmove_candidates=classify_cmove_candidates(orders, m),
    )
```

- [x] **Step 3: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_geo_convoy.py -v`
Expected: 3 pass.

```bash
cd project && git add dipworkpy/geography/convoy.py tests/test_geo_convoy.py
git commit -m "feat(geography): GEO-009 cmove classification + ConvoyGraph extraction

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P3.7: `geography_phase` orchestration

**Files:**
- Create: `project/dipworkpy/geography/service.py`
- Modify: `project/dipworkpy/geography/__init__.py` — re-export
- Test: `project/tests/test_geography_service.py`

- [x] **Step 1: Write failing test**

Create `project/tests/test_geography_service.py`:

```python
from dipworkpy.geo_model import MapRef
from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType


def test_geography_phase_classifies_orders():
    req = GeographyRequest(orders=[
        Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh"),
        Order(nation="Au", utype="A", current="Bud", order=OrderType.mve, dest="ZZZ"),
    ])
    resp = geography_phase(req)
    assert len(resp.order_geo_info) == 2
    assert resp.order_geo_info[0].is_valid is True
    assert resp.order_geo_info[1].is_valid is False
    assert resp.order_geo_info[1].invalidity_code == "GEO-001"


def test_geography_phase_emits_diagnostics():
    req = GeographyRequest(orders=[
        Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Boh"),
    ])
    resp = geography_phase(req)
    # at minimum one diagnostic per order
    assert len(resp.diagnostics) >= 1


def test_geography_phase_normalizes_subfields_in_output():
    req = GeographyRequest(orders=[
        Order(nation="Fr", utype="F", current="SpN", order=OrderType.hld),
    ])
    resp = geography_phase(req)
    assert resp.orders[0].current == "Spa"
    assert resp.order_geo_info[0].resolved_coast == "SpN"
```

- [x] **Step 2: Implement**

Create `project/dipworkpy/geography/service.py`:

```python
"""geography_phase — pure function orchestrating GEO-001..009."""
from __future__ import annotations

from typing import List

from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import OrderGeoInfo
from dipworkpy.geography.coast import normalize_to_superfield, resolve_coast
from dipworkpy.geography.convoy import build_convoy_graph
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.model import GeographyRequest, GeographyResponse
from dipworkpy.geography.rules import (
    classify_convoy, classify_move, classify_support,
)
from dipworkpy.model import Order, OrderType


def _diag(rule: str, severity: str, message: str, order_index=None,
          details=None) -> Diagnostic:
    return Diagnostic(
        phase="geography", rule=rule, severity=severity,
        order_index=order_index, message=message, details=details or {},
    )


def geography_phase(req: GeographyRequest) -> GeographyResponse:
    m = resolve_map_ref(req.map)
    out_orders: List[Order] = []
    geo_info: List[OrderGeoInfo] = []
    diagnostics: List[Diagnostic] = []

    # First pass: cmove classification needs all orders
    cmove_idx = build_convoy_graph(req.orders, m).cmove_candidates

    for i, o in enumerate(req.orders):
        # Normalize: subfields in order refs collapse to superfields
        new_current = normalize_to_superfield(o.current, m)
        new_dest = normalize_to_superfield(o.dest, m) if o.dest else None
        normalized = Order(
            nation=o.nation, utype=o.utype,
            current=new_current, order=o.order, dest=new_dest,
        )

        # Coast resolution
        resolved_coast = resolve_coast(o, m)

        if o.order == OrderType.mve:
            info = classify_move(o, m, order_index=i)
            if i in cmove_idx:
                # Even if direct edge fails, presence of con orders allows
                # the cmove path. Override to moves+is_convoy_move.
                info.is_valid = True
                info.invalidity_code = None
                info.invalidity_reason = None
                info.effective_behavior = "moves"
                info.is_convoy_move = True
        elif o.order in (OrderType.hsup, OrderType.msup):
            # supported_target = o.dest (location of supported unit per DipworkPy notation)
            target = o.dest if o.dest else o.current
            info = classify_support(o, m, supported_target=target, order_index=i)
        elif o.order == OrderType.con:
            # convoyed_dest is the actual move destination; for now use the
            # supported unit's location as a fallback (matches naive case).
            info = classify_convoy(o, m, convoyed_dest=o.dest or o.current, order_index=i)
        else:  # hld or None
            info = OrderGeoInfo(
                order_index=i, is_valid=True,
                effective_behavior="holds_explicit",
            )

        if resolved_coast:
            info.resolved_coast = resolved_coast

        diagnostics.append(_diag(
            info.invalidity_code or "GEO-OK", "info" if info.is_valid else "correction",
            info.invalidity_reason or "ok", order_index=i,
        ))
        out_orders.append(normalized)
        geo_info.append(info)

    cg = build_convoy_graph(req.orders, m)

    return GeographyResponse(
        orders=out_orders, order_geo_info=geo_info,
        convoy_graph=cg, diagnostics=diagnostics,
    )
```

Modify `project/dipworkpy/geography/__init__.py`:

```python
from dipworkpy.geography.service import geography_phase  # noqa: F401
```

- [x] **Step 3: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_geography_service.py -v`
Expected: 3 pass.

```bash
cd project && git add dipworkpy/geography/service.py dipworkpy/geography/__init__.py tests/test_geography_service.py
git commit -m "feat(geography): geography_phase orchestrator

Chains all rules + coast resolution + convoy graph extraction into a single
pure function. order_geo_info travels alongside the normalized orders to
the conflict resolver.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P3.8: Geography FastAPI router

**Files:**
- Create: `project/dipworkpy/geography/api.py`
- Test: integrated in P6 API tests

- [x] **Step 1: Implement**

Create `project/dipworkpy/geography/api.py`:

```python
"""Geography FastAPI router."""
from fastapi import APIRouter

from dipworkpy.geography.model import GeographyRequest, GeographyResponse
from dipworkpy.geography.service import geography_phase

router = APIRouter()


@router.post("/", response_model=GeographyResponse)
def post_geography(req: GeographyRequest) -> GeographyResponse:
    return geography_phase(req)
```

- [x] **Step 2: Smoke-test import**

Run: `cd project && poetry run python -c "from dipworkpy.geography.api import router; print('ok')"`
Expected: `ok`

- [x] **Step 3: Commit**

```bash
cd project && git add dipworkpy/geography/api.py
git commit -m "feat(geography): FastAPI router

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase P4: Conflicter ↔ `order_geo_info` integration

Needs P3. Teaches the existing conflict_game to consume `OrderGeoInfo` and honor the B.4.2.9 / B.4.2.10 asymmetry.

### Task P4.1: Extend `ConflictRequest` and entry point

**Files:**
- Create: `project/dipworkpy/conflict/__init__.py` (empty)
- Create: `project/dipworkpy/conflict/model.py`
- Test: `project/tests/test_conflict_model.py`

- [x] **Step 1: Write failing tests, implement, run, commit**

Create `project/tests/test_conflict_model.py`:

```python
from dipworkpy.conflict.model import ConflictRequest, ConflictResponse
from dipworkpy.model import Order, OrderType


def test_conflict_request_minimal():
    req = ConflictRequest(orders=[
        Order(nation="Au", utype="A", current="Vie", order=OrderType.hld),
    ])
    assert req.order_geo_info is None
    assert req.convoy_graph is None
```

Create `project/dipworkpy/conflict/model.py`:

```python
"""ConflictRequest / ConflictResponse DTOs."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import ConvoyGraph, OrderGeoInfo
from dipworkpy.model import ConflictResolution, Order, Switches


class ConflictRequest(BaseModel):
    orders: List[Order]
    order_geo_info: Optional[List[OrderGeoInfo]] = None
    convoy_graph: Optional[ConvoyGraph] = None
    switches: Switches = Field(default_factory=Switches)


class ConflictResponse(BaseModel):
    resolution: ConflictResolution
    diagnostics: List[Diagnostic] = Field(default_factory=list)
```

Run tests + commit:

```bash
cd project && poetry run python -m pytest tests/test_conflict_model.py -v
git add dipworkpy/conflict/ tests/test_conflict_model.py
git commit -m "feat(conflict): request/response DTOs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P4.2: Parser consumes `order_geo_info` (B.4.2.9 vs B.4.2.10 asymmetry)

**Files:**
- Modify: `project/dipworkpy/conflict_game.py` — parser uses geo info
- Test: `project/tests/test_conflict_geo_info.py`

- [x] **Step 1: Write the asymmetry tests**

Create `project/tests/test_conflict_geo_info.py`:

```python
"""B.4.2.9 vs B.4.2.10 — invalid mve vs invalid hld/sup/con."""
from dipworkpy.conflict_game import conflict_game
from dipworkpy.geo_model import OrderGeoInfo
from dipworkpy.model import Order, OrderType, Situation


def test_invalid_mve_not_hold_supportable():
    """Per B.4.2.9: A unit with an invalid mve does NOT receive hold-support."""
    situation = Situation(orders=[
        Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="ZZZ"),
        Order(nation="Au", utype="A", current="Bud", order=OrderType.hsup, dest="Vie"),
        Order(nation="Ge", utype="A", current="Boh", order=OrderType.mve, dest="Vie"),
    ])
    geo = [
        OrderGeoInfo(order_index=0, is_valid=False, invalidity_code="GEO-001",
                     effective_behavior="holds_no_support"),
        OrderGeoInfo(order_index=1, is_valid=True, effective_behavior="moves"),
        OrderGeoInfo(order_index=2, is_valid=True, effective_behavior="moves"),
    ]
    result = conflict_game(situation, order_geo_info=geo)
    # Vie should be dislodged: hsup from Bud doesn't apply (Vie was "moving")
    vie_result = next(r for r in result.orders if r.current == "Vie")
    assert vie_result.dislodged is True


def test_invalid_sup_holds_and_is_supportable():
    """Per B.4.2.10: A unit with an invalid sup holds and IS hold-supportable."""
    situation = Situation(orders=[
        Order(nation="Au", utype="A", current="Vie", order=OrderType.hsup, dest="ZZZ"),
        Order(nation="Au", utype="A", current="Bud", order=OrderType.hsup, dest="Vie"),
        Order(nation="Ge", utype="A", current="Boh", order=OrderType.mve, dest="Vie"),
    ])
    geo = [
        OrderGeoInfo(order_index=0, is_valid=False, invalidity_code="GEO-004",
                     effective_behavior="holds_supportable"),
        OrderGeoInfo(order_index=1, is_valid=True, effective_behavior="moves"),
        OrderGeoInfo(order_index=2, is_valid=True, effective_behavior="moves"),
    ]
    result = conflict_game(situation, order_geo_info=geo)
    # Vie should NOT be dislodged: Bud's hsup helps Vie hold against Boh
    vie_result = next(r for r in result.orders if r.current == "Vie")
    assert vie_result.dislodged is not True
```

- [x] **Step 2: Modify `conflict_game()` signature**

Modify `project/dipworkpy/conflict_game.py`. Change the parser and entry point to accept optional `order_geo_info`:

```python
# At top of file, import:
from typing import List, Optional
from .geo_model import OrderGeoInfo

# Modify t_field_from_order to accept geo info:
def t_field_from_order(o: model.Order, geo: Optional[OrderGeoInfo] = None) -> t_field:
    strength = int(o.utype) if o.utype in "1234567890" else 1
    # Determine initial t_order based on geo classification
    if geo is None or geo.effective_behavior == "moves":
        torder = t_order_from_order(o)
    elif geo.effective_behavior == "holds_no_support":
        # invalid mve per B.4.2.9 -> internal failed-move state
        torder = t_order.umove
    elif geo.effective_behavior in ("holds_supportable", "holds_explicit"):
        # per B.4.2.10 the unit holds and is hold-supportable
        torder = t_order.none
    else:
        torder = t_order_from_order(o)

    field = t_field(
        player=o.nation,
        order=torder,
        dest=o.dest or o.current,
        xref=o.dest or o.current,
        strength=strength,
        support_strength=strength,
        defensive_strength=strength,
        name=o.current,
        original_order=o,
    )
    if field.order in {t_order.cmove, t_order.nmove}:
        field.strength_a = strength
        field.strength_b = strength
    return field

# Modify parser signature:
def parser(situation: model.Situation,
           order_geo_info: Optional[List[OrderGeoInfo]] = None) -> t_world:
    log = _logger.getChild("parser")
    world = t_world(fields_={}, switches=situation.switches or model.Switches())
    log.info("parser()")
    log.debug("IN situation.orders: %s", dip_eval.LogList(situation.orders, prefix="\n-o "))

    geo_by_index = {g.order_index: g for g in (order_geo_info or [])}
    for i, o in enumerate(situation.orders):
        if world.get_field(o.current):
            raise LookupError(f"fieldname {o.current} twice in current.")
        field = t_field_from_order(o, geo_by_index.get(i))
        world.set_field(field)
    # ... rest unchanged
```

(Apply the analogous change throughout the parser; the rest of the function body is preserved.)

Modify `conflict_game()`:

```python
def conflict_game(situation: model.Situation,
                  order_geo_info: Optional[List[OrderGeoInfo]] = None) -> model.ConflictResolution:
    world = parser(situation, order_geo_info=order_geo_info)
    dip_eval.k1_evaluation(world)
    dip_eval.k2_evaluation(world)
    dip_eval.k3_evaluation(world)
    dip_eval.k4_evaluation(world)
    dip_eval.k0_evaluation(world)
    return writer(world)
```

- [x] **Step 3: Run tests + lint**

Run: `cd project && poetry run python -m pytest tests/test_conflict_geo_info.py -v`
Expected: 2 pass.

Run full suite to confirm no regression:
`cd project && poetry run python -m pytest tests/ -x`
Expected: previously-green tests stay green.

- [x] **Step 4: Commit**

```bash
cd project && git add dipworkpy/conflict_game.py tests/test_conflict_geo_info.py
git commit -m "$(cat <<'EOF'
feat(conflict): consume order_geo_info; honor B.4.2.9/B.4.2.10 asymmetry

Parser maps OrderGeoInfo.effective_behavior to internal t_order:
- moves                -> normal mve (t_order.nmove/cmove)
- holds_no_support     -> t_order.umove (failed move, NOT hold-supportable)
- holds_supportable    -> t_order.none  (regular hold, IS hold-supportable)
- holds_explicit       -> t_order.none

The asymmetry between invalid mve (Gilgamesch B.4.2.9) and invalid
hld/sup/con (B.4.2.10) is realized purely through this state choice; the
k1..k4 algorithms downstream require no change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P4.3: DDL examples 13 & 14 — the asymmetry in pictures

**Files:**
- Create: `project/doc/examples/dwex/13_invalid_move_not_supportable.dwex`
- Create: `project/doc/examples/dwex/14_invalid_support_holds_supportable.dwex`

- [x] **Step 1: Author the DDL files** (mirror the integration tests above as visual examples)

Create `project/doc/examples/dwex/13_invalid_move_not_supportable.dwex`:

```
@dwex
title: 13 — Invalid mve is NOT hold-supportable (B.4.2.9)
desc:  Vie has an invalid mve (to non-existent ZZZ); even with hsup from Bud,
       Vie is dislodged by Boh's attack — invalid-mve order doesn't let the
       unit be hold-supported.

map {
  Vie LA 0,0
  Bud LA 1,-1
  Boh L  -1,0
  Vie -- Bud
  Vie -- Boh
}

orders {
  Au A Vie mve ZZZ
  Au A Bud hsup Vie
  Ge A Boh mve Vie >
}
@end
```

Create `project/doc/examples/dwex/14_invalid_support_holds_supportable.dwex`:

```
@dwex
title: 14 — Invalid sup makes unit hold AND hold-supportable (B.4.2.10)
desc:  Vie's hsup target is invalid; Vie reverts to hold, and Bud's hsup
       DOES help Vie hold against Boh.

map {
  Vie LA 0,0
  Bud LA 1,-1
  Boh L  -1,0
  Vie -- Bud
  Vie -- Boh
}

orders {
  Au A Vie hsup ZZZ
  Au A Bud hsup Vie
  Ge A Boh mve Vie !
}
@end
```

- [x] **Step 2: Render & commit**

Run: `cd project && poetry run python -m dipworkpy.tools.dwex render doc/examples/dwex/13_invalid_move_not_supportable.dwex && poetry run python -m dipworkpy.tools.dwex render doc/examples/dwex/14_invalid_support_holds_supportable.dwex`
Expected: 2 PNGs created.

Note: validation of these examples requires P3 to be wired through the orchestrator (otherwise `conflict_game` is called without `order_geo_info` and behavior reverts). Add an `@pytest.mark.skip` placeholder until P6 connects the pieces, or use a direct integration test in `test_conflict_geo_info.py` (already covered).

```bash
cd project && git add doc/examples/dwex/13_*.dwex doc/examples/dwex/13_*.png doc/examples/dwex/14_*.dwex doc/examples/dwex/14_*.png
git commit -m "$(cat <<'EOF'
docs(dwex): examples 13 & 14 visualize B.4.2.9/B.4.2.10 asymmetry

13: invalid mve -> Vie dislodged despite hsup (the hsup doesn't apply to a
    'moving' unit, even one that failed to move geographically).
14: invalid sup -> Vie holds and hsup from Bud applies, fending off Boh.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase P5: Syntax Service

Parallel to P3/P4 since it only needs P2. Strikes/normalizes input orders + injects hold-defaults for un-ordered units.

### Task P5.1: Syntax models, rules, service, API

**Files:**
- Create: `project/dipworkpy/syntax/__init__.py` (empty)
- Create: `project/dipworkpy/syntax/model.py`
- Create: `project/dipworkpy/syntax/rules.py`
- Create: `project/dipworkpy/syntax/service.py`
- Create: `project/dipworkpy/syntax/api.py`
- Test: `project/tests/test_syntax_service.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_syntax_service.py`:

```python
from dipworkpy.model import Order, OrderType
from dipworkpy.syntax.model import SyntaxRequest
from dipworkpy.syntax.service import syntax_phase


def _o(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current,
                 order=OrderType(order) if order else None, dest=dest)


def test_syn_001_strikes_unknown_nation():
    req = SyntaxRequest(
        orders=[_o("ZZ", "A", "Vie", "hld")],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    # struck order replaced by hold-default for Vie
    assert len(resp.orders) == 1
    assert resp.orders[0].nation == "Au"
    assert resp.orders[0].order == OrderType.hld


def test_syn_004_strikes_unknown_current_field():
    req = SyntaxRequest(
        orders=[_o("Au", "A", "ZZZ", "hld")],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    # struck — but Vie still gets a hold-default
    assert any(o.current == "Vie" for o in resp.orders)
    assert not any(o.current == "ZZZ" for o in resp.orders)


def test_syn_005_double_order_strikes_both():
    req = SyntaxRequest(
        orders=[
            _o("Au", "A", "Vie", "hld"),
            _o("Au", "A", "Vie", "mve", "Boh"),
        ],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    # both struck, hold-default injected
    holds = [o for o in resp.orders if o.current == "Vie"]
    assert len(holds) == 1
    assert holds[0].order == OrderType.hld


def test_syn_008_hold_default_for_unordered_unit():
    req = SyntaxRequest(
        orders=[],
        unit_positions={"Vie": ("Au", "A"), "Lon": ("En", "F")},
    )
    resp = syntax_phase(req)
    nations = {o.nation for o in resp.orders}
    assert nations == {"Au", "En"}
    assert all(o.order == OrderType.hld for o in resp.orders)


def test_syn_emits_diagnostics():
    req = SyntaxRequest(
        orders=[_o("ZZ", "A", "Vie", "hld")],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    codes = {d.rule for d in resp.diagnostics}
    assert "SYN-001" in codes
    assert "SYN-008" in codes
```

- [x] **Step 2: Implement models**

Create `project/dipworkpy/syntax/model.py`:

```python
from __future__ import annotations
from typing import Dict, List, Tuple

from pydantic import BaseModel, Field

from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import MapRef
from dipworkpy.model import Order, Switches


class SyntaxRequest(BaseModel):
    orders: List[Order]
    unit_positions: Dict[str, Tuple[str, str]]
    map: MapRef = Field(default_factory=MapRef)
    switches: Switches = Field(default_factory=Switches)


class SyntaxResponse(BaseModel):
    orders: List[Order]
    diagnostics: List[Diagnostic] = Field(default_factory=list)
```

- [x] **Step 3: Implement rules**

Create `project/dipworkpy/syntax/rules.py`:

```python
"""Syntax rules SYN-001 .. SYN-008."""
from __future__ import annotations

from typing import List, Optional, Set

from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order, OrderType, Switches

VALID_ORDER_TYPES = {OrderType.hld, OrderType.mve, OrderType.hsup, OrderType.msup, OrderType.con}


def is_unknown_nation(o: Order, known: Set[str]) -> bool:
    return o.nation not in known


def is_unknown_unit_type(o: Order, switches: Switches) -> bool:
    if not switches.strict_unit_types:
        return False
    return o.utype not in {"A", "F"}


def field_exists(o: Order, m: MapProtocol) -> bool:
    return m.field_exists(o.current)


def has_known_order_type(o: Order) -> bool:
    return o.order is None or o.order in VALID_ORDER_TYPES


def has_unit_at_current(o: Order, unit_positions: dict) -> bool:
    return o.current in unit_positions
```

- [x] **Step 4: Implement service**

Create `project/dipworkpy/syntax/service.py`:

```python
"""syntax_phase — strikes invalid orders + injects hold-defaults."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from dipworkpy.diag import Diagnostic
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.model import Order, OrderType
from dipworkpy.syntax import rules
from dipworkpy.syntax.model import SyntaxRequest, SyntaxResponse


def _diag(rule: str, severity: str, message: str, idx=None, **details) -> Diagnostic:
    return Diagnostic(phase="syntax", rule=rule, severity=severity,
                      order_index=idx, message=message, details=dict(details))


KNOWN_NATIONS = {"Au", "En", "Fr", "Ge", "It", "Ru", "Tu"}


def syntax_phase(req: SyntaxRequest) -> SyntaxResponse:
    m = resolve_map_ref(req.map)
    sw = req.switches
    diags: List[Diagnostic] = []
    survivors: List[Order] = []

    # Detect doubles (SYN-005)
    counts = Counter(o.current for o in req.orders)
    double_fields = {f for f, c in counts.items() if c > 1}

    for i, o in enumerate(req.orders):
        if rules.is_unknown_nation(o, KNOWN_NATIONS):
            diags.append(_diag("SYN-001", "correction",
                               f"unknown nation {o.nation!r}", idx=i))
            continue
        if rules.is_unknown_unit_type(o, sw):
            diags.append(_diag("SYN-002", "correction",
                               f"unknown utype {o.utype!r}", idx=i))
            continue
        if not rules.has_known_order_type(o):
            diags.append(_diag("SYN-003", "correction",
                               f"unknown order type {o.order!r}", idx=i))
            continue
        if not rules.field_exists(o, m):
            diags.append(_diag("SYN-004", "correction",
                               f"unknown current field {o.current!r}", idx=i))
            continue
        if not rules.has_unit_at_current(o, req.unit_positions):
            diags.append(_diag("SYN-006", "correction",
                               f"no unit at {o.current!r}", idx=i))
            continue
        if o.current in double_fields:
            diags.append(_diag("SYN-005", "correction",
                               f"double order on {o.current}", idx=i))
            continue
        survivors.append(o)

    # SYN-008: inject hold-default for units without a surviving order
    ordered_fields = {o.current for o in survivors}
    for field, (nation, utype) in req.unit_positions.items():
        if field not in ordered_fields:
            survivors.append(Order(
                nation=nation, utype=utype, current=field, order=OrderType.hld,
            ))
            diags.append(_diag("SYN-008", "info",
                               f"hold-default injected for {field}"))

    return SyntaxResponse(orders=survivors, diagnostics=diags)
```

- [x] **Step 5: Implement API**

Create `project/dipworkpy/syntax/api.py`:

```python
from fastapi import APIRouter

from dipworkpy.syntax.model import SyntaxRequest, SyntaxResponse
from dipworkpy.syntax.service import syntax_phase

router = APIRouter()


@router.post("/", response_model=SyntaxResponse)
def post_syntax(req: SyntaxRequest) -> SyntaxResponse:
    return syntax_phase(req)
```

- [x] **Step 6: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_syntax_service.py -v`
Expected: 5 pass.

```bash
cd project && git add dipworkpy/syntax/ tests/test_syntax_service.py
git commit -m "$(cat <<'EOF'
feat(syntax): syntax_phase + SYN-001..008 + FastAPI router

Strikes orders that fail formal/grammatical checks and injects hold-defaults
for every unit lacking a surviving order. Output is always a complete order
set, ready for geography_phase.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase P6: Round Orchestrator + FastAPI mount

Needs P3+P4+P5.

### Task P6.1: Round orchestrator

**Files:**
- Create: `project/dipworkpy/round/__init__.py` (empty)
- Create: `project/dipworkpy/round/orchestrator.py`
- Test: `project/tests/test_round_orchestrator.py`

- [x] **Step 1: Failing tests, implement, run, commit**

Create `project/tests/test_round_orchestrator.py`:

```python
from dipworkpy.model import Order, OrderType
from dipworkpy.round.orchestrator import round_full, RoundRequest


def test_full_round_passes_through_phases():
    req = RoundRequest(
        orders=[Order(nation="Au", utype="A", current="Vie",
                      order=OrderType.mve, dest="Boh")],
        unit_positions={"Vie": ("Au", "A")},
    )
    res = req_round = round_full(req)
    assert res.syntax is not None
    assert res.geography is not None
    assert res.conflict is not None
    assert len(res.diagnostics) > 0
```

Create `project/dipworkpy/round/orchestrator.py`:

```python
"""round_full — chains syntax -> geography -> conflict."""
from __future__ import annotations

from typing import Dict, List, Tuple

from pydantic import BaseModel, Field

from dipworkpy.conflict.model import ConflictRequest, ConflictResponse
from dipworkpy.conflict_game import conflict_game
from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import MapRef
from dipworkpy.geography.model import GeographyRequest, GeographyResponse
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, Switches
from dipworkpy.syntax.model import SyntaxRequest, SyntaxResponse
from dipworkpy.syntax.service import syntax_phase


class RoundRequest(BaseModel):
    orders: List[Order]
    unit_positions: Dict[str, Tuple[str, str]]
    map: MapRef = Field(default_factory=MapRef)
    switches: Switches = Field(default_factory=Switches)


class RoundResult(BaseModel):
    syntax: SyntaxResponse
    geography: GeographyResponse
    conflict: ConflictResponse
    diagnostics: List[Diagnostic] = Field(default_factory=list)


def round_full(req: RoundRequest) -> RoundResult:
    syn = syntax_phase(SyntaxRequest(
        orders=req.orders, unit_positions=req.unit_positions,
        map=req.map, switches=req.switches,
    ))
    geo = geography_phase(GeographyRequest(orders=syn.orders, map=req.map))
    resolution = conflict_game(
        situation=__import__("dipworkpy.model", fromlist=["Situation"]).Situation(
            orders=geo.orders, switches=req.switches,
        ),
        order_geo_info=geo.order_geo_info,
    )
    cnf = ConflictResponse(resolution=resolution)
    return RoundResult(
        syntax=syn, geography=geo, conflict=cnf,
        diagnostics=syn.diagnostics + geo.diagnostics + cnf.diagnostics,
    )
```

Run + commit:

```bash
cd project && poetry run python -m pytest tests/test_round_orchestrator.py -v
git add dipworkpy/round/ tests/test_round_orchestrator.py
git commit -m "feat(round): orchestrator chains syntax -> geography -> conflict

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P6.2: Mount all routers in `api_app.py`

**Files:**
- Create: `project/dipworkpy/api_app.py`
- Create: `project/dipworkpy/round/api.py`
- Create: `project/dipworkpy/conflict/api.py`
- Test: `project/tests/test_api_endpoints.py`

- [x] **Step 1: Write failing tests**

Create `project/tests/test_api_endpoints.py`:

```python
from fastapi.testclient import TestClient

from dipworkpy.api_app import app

client = TestClient(app)


def test_syntax_endpoint():
    r = client.post("/syntax/", json={
        "orders": [],
        "unit_positions": {"Vie": ["Au", "A"]},
    })
    assert r.status_code == 200
    body = r.json()
    assert any(d["rule"] == "SYN-008" for d in body["diagnostics"])


def test_geography_endpoint():
    r = client.post("/geography/", json={
        "orders": [{"nation": "Au", "utype": "A", "current": "Vie",
                    "order": "mve", "dest": "Boh"}],
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["order_geo_info"]) == 1
    assert body["order_geo_info"][0]["is_valid"] is True


def test_round_endpoint_end_to_end():
    r = client.post("/round/", json={
        "orders": [{"nation": "Au", "utype": "A", "current": "Vie",
                    "order": "mve", "dest": "Boh"}],
        "unit_positions": {"Vie": ["Au", "A"]},
    })
    assert r.status_code == 200
```

- [x] **Step 2: Implement remaining routers**

Create `project/dipworkpy/conflict/api.py`:

```python
from fastapi import APIRouter

from dipworkpy.conflict.model import ConflictRequest, ConflictResponse
from dipworkpy.conflict_game import conflict_game
from dipworkpy.model import Situation

router = APIRouter()


@router.post("/", response_model=ConflictResponse)
def post_conflict(req: ConflictRequest) -> ConflictResponse:
    sit = Situation(orders=req.orders, switches=req.switches)
    resolution = conflict_game(sit, order_geo_info=req.order_geo_info)
    return ConflictResponse(resolution=resolution)
```

Create `project/dipworkpy/round/api.py`:

```python
from fastapi import APIRouter

from dipworkpy.round.orchestrator import RoundRequest, RoundResult, round_full

router = APIRouter()


@router.post("/", response_model=RoundResult)
def post_round(req: RoundRequest) -> RoundResult:
    return round_full(req)
```

Create `project/dipworkpy/api_app.py`:

```python
"""FastAPI app mounting every service router."""
from fastapi import FastAPI

from dipworkpy.conflict.api import router as conflict_router
from dipworkpy.geography.api import router as geography_router
from dipworkpy.round.api import router as round_router
from dipworkpy.syntax.api import router as syntax_router


def create_app() -> FastAPI:
    app = FastAPI(title="DipworkPy")
    app.include_router(syntax_router, prefix="/syntax", tags=["syntax"])
    app.include_router(geography_router, prefix="/geography", tags=["geography"])
    app.include_router(conflict_router, prefix="/conflict", tags=["conflict"])
    app.include_router(round_router, prefix="/round", tags=["round"])

    @app.get("/")
    def root() -> dict:
        return {"service": "dipworkpy", "endpoints": [
            "/syntax", "/geography", "/conflict", "/round",
        ]}

    return app


app = create_app()
```

- [x] **Step 3: Run + commit**

Run: `cd project && poetry run python -m pytest tests/test_api_endpoints.py -v`
Expected: 3 pass.

```bash
cd project && git add dipworkpy/api_app.py dipworkpy/conflict/api.py dipworkpy/round/api.py tests/test_api_endpoints.py
git commit -m "$(cat <<'EOF'
feat(api): mount syntax, geography, conflict, round routers

Each service has its own HTTP endpoint; the round/ endpoint is a convenience
that chains them. Third parties can build UIs against any subset.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase P7: DATC Bug Analysis (parallel, independent)

### Task P7.1: Analyze 6.D.2 / 6.D.3 / 6.F.1

**Files:**
- Create: `project/doc/DATC_ANALYSIS.md`
- Possibly modify: `project/dipworkpy/eval/eval_k2.py` and/or `eval_k3.py`
- Test: `project/tests/test_conflict_datc.py` (existing)

- [x] **Step 1: Re-read each failing DATC test from `tests/TEST_CASES_DATC.md`**

Run: `cd project && cat tests/TEST_CASES_DATC.md | head -200`
Goal: locate the entries for 6.D.2, 6.D.3, 6.F.1. Extract DipworkPy notation + expected outcome.

- [x] **Step 2: For each case, run only that test with verbose output**

Run: `cd project && poetry run python -m pytest tests/test_conflict_datc.py -v -k "6_D_2 or 6_D_3 or 6_F_1"`
Capture the actual vs expected divergence.

- [x] **Step 3: For each case, draft a section in `DATC_ANALYSIS.md`**

Create `project/doc/DATC_ANALYSIS.md` with this structure:

```markdown
# DATC Failure Analysis

## 6.D.2 — <title>
**DATC spec:** ...
**Our actual output:** ...
**Diff:** ...
**Phase:** k2 / k3 / k4
**Verdict:** [bug | deliberate variant]
**Fix:** [code change in eval_k*.py, switch added, or documented as variant]

## 6.D.3 — ...
## 6.F.1 — ...
```

- [x] **Step 4: Implement fixes (per case, separate commits)**

For each case where verdict = bug: edit `dipworkpy/eval/eval_k*.py`. For each case where verdict = variant: add a switch to `Switches` and gate the new behavior on it.

After each fix:
- Run: `cd project && poetry run python -m pytest tests/test_conflict_datc.py -v`
- Verify no regressions elsewhere: `poetry run python -m pytest tests/ -x`

- [x] **Step 5: Commit (one commit per case)**

Example for a bug fix:

```bash
cd project && git add dipworkpy/eval/eval_k3.py doc/DATC_ANALYSIS.md
git commit -m "$(cat <<'EOF'
fix(eval): DATC 6.D.2 support-cut treatment

The k2 phase was treating same-nation support attempts as cuts. DATC 6.D.2
requires that a nation cannot cut its own support; per documented analysis
in DATC_ANALYSIS.md this is a bug rather than a deliberate variant.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

(Repeat per case; the actual edits depend on the analysis.)

---

## Phase P8: DipNet Cluster Analysis

Needs P3+P4 wired through (so the Geography reduces `?-inconclusive`).

### Task P8.1: Add `--cluster-failures` to the DipNet reporter

**Files:**
- Modify: `project/test_data_pipeline/run_dipnet_tests.py`
- Test: extend its test (if present) or smoke via CLI

- [x] **Step 1: Inspect current reporter**

Run: `cd project && head -100 test_data_pipeline/run_dipnet_tests.py`

- [x] **Step 2: Add `--cluster-failures` flag**

Modify `run_dipnet_tests.py`. Add CLI arg and implementation:

```python
# In argument parser:
parser.add_argument(
    "--cluster-failures",
    action="store_true",
    help="Group failures by order-type signature and dump top-N clusters",
)

# After running all tests:
if args.cluster_failures:
    from collections import Counter, defaultdict
    signatures: Counter = Counter()
    examples: dict = defaultdict(list)
    for case in failures:
        sig = _order_signature(case)
        signatures[sig] += 1
        if len(examples[sig]) < 3:
            examples[sig].append(case.game_id)
    print("\n=== FAILURE CLUSTERS (top 20) ===")
    for sig, count in signatures.most_common(20):
        print(f"  {count:4d}  {sig}")
        for ex in examples[sig]:
            print(f"        e.g. {ex}")
```

Add helper:

```python
def _order_signature(case) -> str:
    """Order-type counts for the test case, as a stable signature string."""
    from collections import Counter
    c = Counter(o.order.value if o.order else "none" for o in case.orders)
    return ",".join(f"{k}:{v}" for k, v in sorted(c.items()))
```

- [x] **Step 3: Run and dump clusters**

Run: `cd project && make test-dipnet-quick -- --cluster-failures > doc/DIPNET_CLUSTERS.md`
Expected: top clusters in the output file.

- [x] **Step 4: Commit**

```bash
cd project && git add test_data_pipeline/run_dipnet_tests.py doc/DIPNET_CLUSTERS.md
git commit -m "$(cat <<'EOF'
feat(dipnet): cluster-failures reporter

Groups failing cases by order-type signature and shows top-20 patterns
with 3 example game IDs each. Turns a 466-failure pile into a triaged
backlog ready for cluster-driven fixes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task P8.2: Iterative cluster-driven fixes (one cluster per commit)

For each of the top clusters in `DIPNET_CLUSTERS.md`:
1. Pick the cluster with the most failures.
2. Inspect 3 example games (game IDs from the report) — locate the test case in the dataset, examine the order pattern.
3. Hypothesize the algorithm phase responsible (k1..k4).
4. Write a minimal DDL example reproducing the failure (`project/doc/examples/dwex/dipnet_clusterNNN.dwex`).
5. Fix the bug in `eval/eval_kX.py` or add a switch.
6. Re-run `make test-dipnet-quick` and report new PASS / FAIL / INCONCLUSIVE.
7. Commit with cluster signature in the message.

Continue until DipNet PASS ≥ 80 %.

---

## Phase P9: DDL Examples Sweep

Continuous from P1.

### Task P9.1: Examples 06–12

Author and commit each, one per task, following the DDL template:

- `06_support_cut.dwex` — support cut by attack
- `07_basic_convoy.dwex` — A Lon → Bel via F NTH con
- `08_convoy_disrupted.dwex` — F NTH dislodged, convoy fails
- `09_chain_of_three.dwex` — circular moves (k4)
- `10_dislodgement.dwex` — simple dislodgement
- `11_pattfield.dwex` — pattfield generation
- `12_subfield_resolution.dwex` — F Spa mve MID via SpS

For each: write the `.dwex`, render the PNG, validate via `dwex validate`, commit `.dwex + .png`.

### Task P9.2: EXAMPLES.md generator

**Files:**
- Create: `project/dipworkpy/tools/dwex/generate_index.py`
- Create: `project/doc/EXAMPLES.md` (generated)

- [x] **Step 1: Implement generator**

Create `project/dipworkpy/tools/dwex/generate_index.py`:

```python
"""Generate doc/EXAMPLES.md from all .dwex files."""
from __future__ import annotations

import sys
from pathlib import Path

from dipworkpy.tools.dwex.lang import parse_file


def generate(dwex_dir: Path, out: Path) -> None:
    lines = ["# DDL Examples", ""]
    for p in sorted(dwex_dir.rglob("*.dwex")):
        doc = parse_file(p)
        png_rel = p.with_suffix(".png").relative_to(out.parent)
        lines.append(f"## {doc.title}")
        lines.append("")
        if doc.description:
            lines.append(doc.description)
            lines.append("")
        lines.append(f"![{doc.title}]({png_rel})")
        lines.append("")
        lines.append("<details><summary>DDL source</summary>")
        lines.append("")
        lines.append("```")
        lines.append(p.read_text())
        lines.append("```")
        lines.append("</details>")
        lines.append("")
    out.write_text("\n".join(lines))


if __name__ == "__main__":
    generate(Path(sys.argv[1]), Path(sys.argv[2]))
```

- [x] **Step 2: Run + commit**

Run: `cd project && poetry run python -m dipworkpy.tools.dwex.generate_index doc/examples/dwex doc/EXAMPLES.md`
Expected: `doc/EXAMPLES.md` regenerated.

```bash
cd project && git add dipworkpy/tools/dwex/generate_index.py doc/EXAMPLES.md
git commit -m "feat(dwex): EXAMPLES.md generator

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task P9.3: Makefile targets

- [x] **Step 1: Add examples targets**

Modify `project/Makefile`:

```makefile
examples:		## Render all DDL examples + regenerate EXAMPLES.md
	poetry run python -m dipworkpy.tools.dwex render-all doc/examples/dwex
	poetry run python -m dipworkpy.tools.dwex.generate_index doc/examples/dwex doc/EXAMPLES.md

examples-check:	## Verify DDL examples render and validate
	poetry run python -m pytest tests/test_dwex_examples.py -v
```

- [x] **Step 2: Commit**

```bash
cd project && git add Makefile
git commit -m "build: make examples / examples-check targets

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Final Verification

After all phases complete:

1. Full test suite: `cd project && poetry run python -m pytest tests/ -v`
2. Lint clean: `cd project && poetry run ruff check . && poetry run mypy .`
3. DipNet quick: `cd project && make test-dipnet-quick` — PASS ≥ 80 %
4. DATC: `cd project && make test-datc` — all 10 pass (or remaining failures documented as switches)
5. DDL examples: `cd project && make examples-check` — all green
6. API smoke: `cd project && poetry run uvicorn dipworkpy.api_app:app --port 8000` — visit `/docs`, exercise each endpoint
7. Confirm: no committed file under `git ls-files` references the `pas/` directory

```bash
cd project && git ls-files | xargs grep -l "pas/" 2>/dev/null
```

Expected: empty.

---
