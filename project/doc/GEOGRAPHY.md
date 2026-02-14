# Geography Implementation Notes

## Current State

The Conflict Resolver is geography-agnostic except for convoy route validation. Currently `convoy_routing_engine` has two modes:
- `"always"` -- all convoy attempts are assumed to have valid routes (default)
- `"fixed:Vie--Mun;..."` -- explicitly specified routes

There is no geographic border map or adjacency validation.

## What the Conflict Resolver Needs from Geography

Only one thing: **convoy route validation**. Given a set of convoy orders and a convoyed army, determine whether a chain of fleets connects the army's origin to its destination via sea territories.

Everything else (move legality, support reach, fleet vs army terrain) is handled in the Geography phase *before* conflict resolution.

## Superfields vs Subfields

The Conflict Resolver works exclusively on **superfields**:

| Superfield | Subfields | Notes |
|------------|-----------|-------|
| `Spa` | `SpN`, `SpS` | Spain north coast, south coast |
| `StP` | `StN`, `StS` | St. Petersburg north, south |
| `Bul` | `BuE`, `BuS` | Bulgaria east coast, south coast |

Subfield resolution must happen in the Geography phase. After that phase, only superfield codes appear in orders passed to the Conflict Resolver.

Other phases (Geography validation, Retreats) may need subfield information to determine which coast a fleet occupies or can retreat to.

## What Geography Validation Must Check

For each order type:

### Move (`mve`)
- **Army**: destination must be an adjacent land territory, OR reachable via convoy
- **Fleet**: destination must be an adjacent sea or coastal territory
- Fleet subfield matters: `F StN` can reach BAR but not BOT; `F StS` can reach BOT but not BAR

### Hold (`hld`)
- Always valid (unit stays put)

### Hold Support (`hsup`)
- Supporting unit must be able to move to the supported territory (even though it doesn't actually move)
- This means the same adjacency rules as `mve` apply

### Move Support (`msup`)
- Supporting unit must be able to move to the *destination* of the supported move
- The supporting unit does not need to be adjacent to the supported unit itself

### Convoy (`con`)
- Fleet must be on a sea territory (not coastal)
- Fleet must be on a territory that connects the army's origin to its destination

## The Convoy Problem

Convoy validation is the hardest part because:

1. **Circular dependency**: An army's move might require a convoy, but whether the convoy succeeds depends on whether the convoying fleet is dislodged, which depends on other conflicts
2. **Implicit convoys (original rules)**: In the original printed rules, a convoy does not need to be explicitly ordered. If an army moves to a non-adjacent territory and fleets happen to form a chain, the convoy is assumed
3. **Ambiguous routes**: Multiple convoy routes may exist. If one is disrupted, the move might still succeed via another route
4. **The paradox cases**: Some situations create logical paradoxes (e.g., "Pandin's paradox") where the resolution of a convoy depends on itself

The Conflict Resolver already handles paradoxes and disruption logic (k1 phase). What it needs is the geographic "does a route exist?" answer.

## Implementation Plan

### Phase 1: Territory adjacency map
Build a data structure mapping each territory to its neighbors, distinguishing:
- Land adjacencies (army movement)
- Sea adjacencies (fleet movement)
- Coast information (which subfields connect to which sea zones)

### Phase 2: Convoy route finder
Given a set of fleet positions on sea territories, determine whether a chain connects two coastal territories. The existing `graphs.py` module already has pathfinding algorithms (`find_shortest_path_bfs`, `find_shortest_path_dfs`) that can be reused.

### Phase 3: Integration with Conflict Resolver
Replace `convoy_routing_engine: "always"` with actual geographic validation. The k1 phase in `eval_k1.py` already has the framework for convoy evaluation -- it just needs a real route checker instead of the placeholder.

### Phase 4: Full Geography validation phase
Implement as a pre-processing step before conflict resolution. Validate all orders against the adjacency map and convert invalid orders to holds.
