# DipworkPy — Implementation Documentation

DipworkPy is a Python re-implementation of the German-PBM-style Diplomacy adjudicator, structured as a set of HTTP services: **Syntax → Geography → Conflict → Round**. This documentation covers the implementation: how the pipeline is built, what design rules apply at each phase, and how the test suites validate it.

For rendering instructions see [README.md](README.md). For game rules see the repo-level [`docs/`](../../docs/).

---

## Pipeline overview

```
        Order[] + unit_positions
                │
                ▼   syntax_phase()       SYN-001..008: strikes / hold-defaults
        Order[]
                │
                ▼   geography_phase()    GEO-001..009: classifies orders per Gilgamesch B.2.6.1
        Order[]
        OrderGeoInfo[]                   (carries B.4.2.9/B.4.2.10 asymmetry as marker)
        ConvoyGraph
                │
                ▼   conflict_game()      k1..k4 + k0
        ConflictResolution
                │
                ▼   round_full()         orchestrator (HTTP `/round`)
```

Each phase is also independently callable via HTTP:

| Endpoint | Pure function | Purpose |
|----------|---------------|---------|
| `POST /syntax`     | `syntax_phase`     | Strike invalid orders, inject hold-defaults |
| `POST /geography`  | `geography_phase`  | Classify reachability, resolve coasts, extract ConvoyGraph |
| `POST /conflict`   | `conflict_game`    | Resolve conflicts using `OrderGeoInfo` markers |
| `POST /round`      | `round_full`       | Chain all three for convenience |

---

## Core docs

| Doc | What's in it |
|-----|--------------|
| **[PHASES.md](PHASES.md)**         | All six Diplomacy round phases with status (implemented / not implemented) |
| **[GEOGRAPHY.md](GEOGRAPHY.md)**   | Map representation, FIELDS-spec semantics, ConvoyGraph notes |
| **[EXAMPLES.md](EXAMPLES.md)**     | **14 rendered DDL examples** — visual + regression tests |
| **[DATC_ANALYSIS.md](DATC_ANALYSIS.md)**  | Per-case analysis of historically-failing DATC tests (6.D.2/3, 6.F.1) |
| **[DIPNET_CLUSTERS.md](DIPNET_CLUSTERS.md)** | Cluster-grouped DipNet failure analysis (96.4 % PASS achieved) |
| **[TEST_EXPANSION.md](TEST_EXPANSION.md)** | Test infrastructure: STPSYR, DATC, DipNet runners |

## Spec & plan (repo root)

Design and execution artefacts live one level up — they cover the whole re-architecture, not just `project/`:

- **[Comprehensive design spec](../../docs/superpowers/specs/2026-05-12-dipworkpy-comprehensive-design.md)** — 9 sections covering services, geography, syntax, conflict, DDL, tests, roadmap
- **[Implementation plan](../../docs/superpowers/plans/2026-05-12-dipworkpy-implementation.md)** — 10 phases (P0..P9), all complete
- **[Status snapshot 2026-05-13](../../docs/superpowers/STATUS-2026-05-13.md)** — current state, deferred items, next steps

---

## DDL — Diplomacy Diagram Language

Every example is a single `.dwex` source file producing four artefacts:

- A PNG diagram (matplotlib renderer)
- A `Situation` for the conflict engine
- An expected `ConflictResolution` (driven by `!` / `>` markers in the source)
- An inline `MapDefinition` (so examples need no external map)

The 14 examples in [EXAMPLES.md](EXAMPLES.md) cover holds, moves, bounces, supports, convoys, dislodgement, pattfields, subfield resolution, and the B.4.2.9 / B.4.2.10 invalid-order asymmetry.

```bash
make examples         # render all PNGs, rebuild EXAMPLES.md
make examples-check   # run the parametrized regression test
```

DDL source lives in [`examples/dwex/`](examples/dwex/).

---

## Tasks

Historical work breakdown in [`tasks/`](tasks/) — task series TASK-TESTEX-001..005 covering the test-suite expansion effort that produced the DipNet test runner.

---

## Conventions used throughout

- **Notation**: see [`project/NOTATION.md`](../NOTATION.md) (one level up). Nations as 2-letter codes (`Au`, `En`), territories as 3-letter codes (`Vie`, `NTH`), orders as 3-4 letter ops (`mve`, `hsup`).
- **Field types**: `LA` inland-army, `LCB` simple-coast, `LCA` split-coast superfield, `LCF` subfield, `LC` plain coast, `L` pure inland, `O` ocean, `COL` off-map.
- **Order classification**: `gültig` → `wirksam` → `durchgesetzt` (Gilgamesch B.2.6.1/.2/.3).
- **PBM asymmetry**: invalid `mve` → unit stays but NOT hold-supportable (B.4.2.9); invalid `hld`/`sup`/`con` → unit holds AND is hold-supportable (B.4.2.10).
