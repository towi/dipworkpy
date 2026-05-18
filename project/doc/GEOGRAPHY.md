# Geography Implementation Notes

## Current State

Geography is represented as a JSON graph in `dipworkpy/geography/map/data/standard.json`.
Fields are nodes; directed edges carry three independent passability values:

- `army` — army movement/support reachability
- `fleet` — fleet movement/support reachability, including coast-required values such as `SpS`
- `convoy_move` — coast/sea connectivity for convoy-route extraction

The Geography phase validates direct movement with unit type (`A`/`F`), resolves subfields to superfields, and extracts a convoy graph for convoyed army moves. The Conflict Resolver still remains geography-agnostic internally; it consumes normalized orders plus `OrderGeoInfo` markers.

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

## JSON Graph Format

The bundled map uses this shape:

```json
{
  "map_id": "standard",
  "fields": {
    "Spa": {"type": "LC", "is_supply_center": true, "neighbor_order": ["Gas", "Mar", "LYO"]},
    "SpS": {"type": "LCF", "sub_of": "Spa", "neighbor_order": ["Mar", "LYO"]},
    "LYO": {"type": "O"}
  },
  "edges": [
    {"from": "SpS", "to": "Mar", "army": "-", "fleet": "ja", "convoy_move": "ja"},
    {"from": "SpS", "to": "LYO", "army": "-", "fleet": "ja", "convoy_move": "ja"},
    {"from": "Spa", "to": "LYO", "army": "nein", "fleet": "-", "convoy_move": "ja"}
  ]
}
```

`edges` is an array, not an object, because edge order is semantically meaningful for retreat ordering. `neighbor_order` stores each field's clockwise border ring. `MapDefinition` keeps tuple keys internally for graph lookups and still accepts legacy `"from:to"` objects for compatibility. `ConvoyGraph` uses `"from:to"` strings only for its compact API serialization.

## Implemented Behavior

### Territory adjacency graph

`StandardMap` and `InlineMap` expose fields, superfield/subfield relationships, and directed edges through `MapProtocol`. Movement code never treats adjacency as a plain neighbor lookup; it checks the edge passability for the unit type.

### Army/fleet movement

- Armies require an `army: "ja"` edge, or a coast-required literal that matches the superfield being entered/exited.
- Fleets require a `fleet: "ja"` edge, or a literal subfield value such as `SpS`, `PeN`, `BuE`.
- Split-coast superfields expand to their subfields for reachability checks, then output orders are normalized back to the superfield.

### Convoy route graph

`build_convoy_graph()` extracts:

- `sea_edges`: sea-to-sea links between ordered convoying fleets
- `coastal_edges`: coast-to-sea links between army endpoints and convoying fleets
- `convoyer_fields`: fields containing `con` orders
- `cmove_candidates`: army move indices that have an actual graph route

Multi-sea routes are supported, e.g. coast → `NTH` → `ENG` → coast.

### Retreat ordering

`retreat_options()` interprets `neighbor_order` as a clockwise ring. Given a dislodged field and the field the attack came from, candidates alternate right-hand side first, then left-hand side, expanding outward around the ring. The special token `ex` is always appended; if every candidate is occupied/patt or unreachable for the unit type, the response is just `["ex"]`.

The Geography API exposes this as `POST /geography/retreat-options` with optional `occupied_fields` filtering.

### Remaining integration note

The Geography phase now decides whether a move is a convoy move and whether convoy orders are geographically connected. The conflict engine's historical `convoy_routing_engine` switch remains for low-level tests/backward compatibility; full round evaluation should prefer the Geography phase output.
