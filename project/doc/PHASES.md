# Diplomacy Game Round Phases

A complete Diplomacy game round processes orders through a pipeline of phases. Each phase assumes the previous phase has
already validated and normalized the orders.

## Phase Pipeline

```
Syntax → Geography → Conflict Resolution → Retreats → Support Centers → Buildup/Dissolve
```

## Phase 1: Syntax

**Status:** Implemented (`dipworkpy/syntax/service.py`)

Applies PBM-style strike-or-hold-default rules (SYN-001..009). Outputs always a complete order set — every unit either has its surviving user-issued order or an injected `hld` default.

- **SYN-001** unknown nation → strike
- **SYN-003** unknown order type → strike
- **SYN-004** unknown field name → strike (geography catches valid-but-unreachable fields under GEO-001 instead)
- **SYN-005** double order on same field → strike all conflicting orders (orders SYN-009 strikes are excluded from the doubles count, so a foreign order can't shadow the owner's own order)
- **SYN-006** order on a field with no unit → strike
- **SYN-009** ordered unit belongs to another nation → strike (SYN-008 then hold-injects the real owner); right owner but wrong unit letter → corrected in place from the board (advisory, per DATC 6.B.13)
- **SYN-008** for each unit in `unit_positions` without a surviving order: inject `hld`

SYN-002 (unknown unit type) and SYN-007 (unit/field-type mismatch) are gated on the `strict_unit_types` switch and currently default off.

Diagnostics: every rule emits a `Diagnostic` with `phase="syntax"`, the rule id, severity, and (where applicable) `order_index`.

## Phase 2: Geography

**Status:** Implemented (`dipworkpy/geography/service.py`)

Per Gilgamesch B.2.6, this phase classifies orders as **gültig / wirksam / durchgesetzt**. Geography handles "gültig"; "wirksam" and "durchgesetzt" belong to the conflict resolver. Geography does NOT rewrite orders into holds — invalid orders are classified via `OrderGeoInfo.effective_behavior`, preserving the B.4.2.9 / B.4.2.10 asymmetry (invalid `mve` → unit stays but not hold-supportable; invalid `hld`/`sup`/`con` → unit holds and is hold-supportable).

Rules:

- **GEO-001..003**: move validity — destination exists, start ≠ destination, destination reachable (per FIELDS `army/fleet` passability or possible convoy chain)
- **GEO-004**: support reachability — supporter must reach supported destination from a direct neighbour (no convoy / no furt, Gilgamesch B.3.1.1 Fn. 4)
- **GEO-005..006**: convoy preconditions — convoyer on sea, adjacent to both army start and dest
- **GEO-007**: subfield coast resolution when the move target uniquely determines the coast (e.g. `F Spa mve LYO` → SpS)
- **GEO-008**: superfield normalisation on output (orders going to the conflict resolver use Spa, not SpN)
- **GEO-009**: classify `mve` as `cmove` when ordered convoyers form a route; unflagged moves with a direct land route stay land moves (B.3.2.14 sentence 3)
- **GEO-010**: explicit `mve [Convoy]` flag per Gilgamesch B.3.2.14, carried as `Order.via_convoy`

Additional output: `ConvoyGraph` — sea/coastal edges relevant to convoy routing, used by `eval_k1` for convoy route validation.

## Phase 3: Conflict Resolution

**Status:** Implemented (`conflict_game.py`)

The core algorithm. Resolves conflicts between competing orders using a 5-step internal pipeline:

```
parser → k1 (convoys) → k2 (support cutting) → k3 (move conflicts) → k4 (chains) → k0 (uncontested) → writer
```

**Assumptions:**

- All orders are syntactically and geographically valid
- Works on superfields only (Spa, not SpN/SpS)
- `msup`/`con` dest field = starting field of the referenced unit (uniquely identifies it)

**Output:** `ConflictResolution` with order results (succeeded/failed/dislodged) and pattfields (territories unavailable
for retreats).

See `project/dipworkpy/eval/README.md` for the internal algorithm details.

## Phase 4: Retreats

**Status:** Partial — `geography/retreat.py:retreat_options` enumerates a unit's candidate retreat fields (using the right-hand-rule ordering plus `ex` for disband). The actual resolution — pairing dislodged units against their options, detecting retreat conflicts, disbanding — is not yet implemented.

Input: Dislodged units from Conflict Resolution + pattfields.

## Phase 5: Support Centers

**Status:** Not implemented

Count supply centers controlled by each nation after all movement and retreats. A supply center is controlled by the
nation whose unit last occupied it.

## Phase 6: Buildup and Dissolve

**Status:** Not implemented

Nations with more supply centers than units may build new units on unoccupied home supply centers. Nations with fewer
supply centers than units must disband excess units.

## Notation Convention

The `dest` field in DipworkPy orders identifies the **referenced unit by its starting position**, not the move target:

| Order  | Example             | `dest` meaning                                              |
|--------|---------------------|-------------------------------------------------------------|
| `mve`  | `Au A Vie mve Mun`  | Move destination (Mun)                                      |
| `hld`  | `Au A Vie hld`      | None                                                        |
| `hsup` | `En F ENG hsup NTH` | Location of held unit (NTH)                                 |
| `msup` | `En F ENG msup Lon` | Starting field of moving unit (Lon, not where it's going)   |
| `con`  | `Ge F NTH con Kie`  | Starting field of convoyed army (Kie, not where it's going) |

This convention works because each territory can hold at most one unit, so the starting field uniquely identifies the
unit and thus its order.
