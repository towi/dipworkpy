# Diplomacy Game Round Phases

A complete Diplomacy game round processes orders through a pipeline of phases. Each phase assumes the previous phase has
already validated and normalized the orders.

## Phase Pipeline

```
Syntax → Geography → Conflict Resolution → Retreats → Support Centers → Buildup/Dissolve
```

## Phase 1: Syntax Validation

**Status:** Not implemented

Validates that orders are syntactically correct:

- **Invalid fields**: `Au A Tri mve ZZZ` -- ZZZ does not exist → order changed to hold
- **Invalid order types**: `Au A Tri celebrates` -- no such order → changed to hold
- **Missing units**: `A Tri hld` but there is no army in Trieste → order removed entirely
- **Unit type mismatches**: Fleet ordered to move inland-only, army ordered to move sea-only

Output: All surviving orders have valid syntax (known nations, territories, unit types, order types).

## Phase 2: Geography Validation

**Status:** Not implemented

Checks that orders are geographically possible:

- Can the unit reach the destination from its current position?
- For armies: is there a land path (or possible convoy route)?
- For fleets: is there a sea/coastal path?
- For supports: can the supporting unit reach the supported destination?
- For convoys: is the fleet on a sea territory adjacent to the required route?

**Complexity:** This phase is very difficult because any coast-to-coast army move could potentially be made legal by a
convoy chain. Determining whether a convoy route *could* exist requires analyzing the entire set of orders together.

**Subfield handling:** This phase resolves subfield ambiguities (SpN vs SpS, StN vs StS, BuE vs BuS). After this phase,
the Conflict Resolver only sees superfields (Spa, StP, Bul).

Output: All surviving orders are geographically valid. Orders that cannot be executed are changed to hold.

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

See `project/dipworkpy/dip_eval/README.md` for the internal algorithm details.

## Phase 4: Retreats

**Status:** Not implemented

Dislodged units must retreat to an adjacent, unoccupied territory that is not a pattfield. If no valid retreat exists,
or if two dislodged units try to retreat to the same territory, the unit is disbanded.

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
