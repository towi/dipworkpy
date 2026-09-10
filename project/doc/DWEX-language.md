# DWEX language reference

DWEX (Diplomacy Diagram Example) is a small Markdown-adjacent source format for executable Diplomacy diagrams. A `.dwex` file is parsed into:

- a PNG diagram,
- an inline map for the example,
- a `Situation` for `conflict_game`, and
- an expected `ConflictResolution` using result markers in the order list.

Use DWEX for compact, visual regression examples. It is intentionally smaller than the full game-order syntax and focuses on one scenario per file.

## File shape

Every file starts with `@dwex` and ends with `@end`:

```text
@dwex
title: 03 — Equal Bounce
desc:  Two armies of equal strength move to the same field.

map {
  Vie LA 0,0
  Mun LA 2,0
  Tyr L  1,1
  Vie -- Tyr
  Mun -- Tyr
}

orders {
  Au A Vie mve Tyr !
  Ge A Mun mve Tyr !
}
@end
```

Recognized top-level items are:

| Item | Required | Purpose |
|------|----------|---------|
| `title:` | yes | Diagram/example title, also used as the heading in `EXAMPLES.md` |
| `desc:` | no | Free text description; continuation lines are indented |
| `map {}` | usually | Inline fields and edges for rendering/conversion |
| `units {}` | no | Explicit unit placement when no orders are needed |
| `orders {}` | usually | Orders plus optional expected result markers |
| `switches {}` | no | Conflict resolver switches for the scenario |
| `pattfields {}` | no | Expected pattfields |
| `pragmas {}` | no | Rendering options |

## Field names

Prefer canonical field names from the standard map data / FIELDS source. For example, use `ENG` for English Channel, not legacy aliases such as `CHN`.

Artificial names are acceptable only when the example is deliberately about invalid input, e.g. `ZZZ` in invalid-order examples.

## `map {}`

The map block contains field declarations and edge declarations.

### Fields

```text
<Name> <Type> <x>,<y>
```

Examples:

```text
Vie LA 0,0
NTH W  1,0
ENG W  2,-1
```

Common field types:

| Type | Meaning |
|------|---------|
| `L` | land |
| `LA` | land with army placement |
| `W` / `O` | water / ocean |
| `LC`, `LCA`, `LCB`, `LCF` | coast-related field types used by geography docs |
| `COL` | off-map / special field |

Coordinates are renderer coordinates only; they do not imply reachability.

### Edges

```text
A -- B      # army, fleet, and convoy-move passable
A --A B     # army-passable only
A --F B     # fleet-passable only
A --C B     # convoy-move passable only
A -> B      # directed edge; variants such as ->F work too
```

Edges are local to the example's inline map. Add only what the scenario needs.

## `orders {}`

Order lines use DipworkPy's compact notation:

```text
<Nation> <Unit> <Current> <Order> [Dest] [markers]
```

Examples:

```text
Au A Vie hld
Au A Vie mve Mun !
Au A Boh hsup Vie
Au A Boh msup Vie !
En F NTH con Lon
Ge A Mun hld >
```

Supported order codes are:

| Code | Meaning | `dest` means |
|------|---------|--------------|
| `hld` | hold | omitted |
| `mve` | move | target field |
| `hsup` | support hold | field of supported unit |
| `msup` | support move | starting field of supported moving unit |
| `con` | convoy | starting field of convoyed army |

For `msup` and `con`, `dest` intentionally names the referenced unit's starting field, not the target of that unit's move. Earlier phases are responsible for disambiguating/validating the full order.

### Explicit support-of-movement notation

`msup` also has an explicit form that names the supported movement directly —
useful when the supported unit's own order is not present in the document
(the renderer would otherwise draw the straight diamond fallback):

```text
Ge A Mun sup Ber mve Kie
Ge A Mun msup Ber - Kie
Ge A Mun sup A Ber mve Kie
Ge A Mun sup Ge A Ber mve Kie
```

Aliases: the keyword may be `sup` or `msup`; the movement code may be `mve`
or `-`; the supported unit may be written as `Ber`, `A Ber`, or `Ge A Ber`.
The curve always starts at the supporter (`Mun`), bows through the
supported unit (`Ber`), and ends at the movement target (`Kie`) — same Bezier
shape as `con`. The implicit form (`Ge A Mun msup Ber`) resolves the target
from the supported unit's own `mve` order; the explicit form's target wins
when both are present.

### Per-order annotations and comments

Order lines accept trailing annotations (all stripped before parsing):

- **`via`** — explicit convoy move (Gilgamesch B.3.2.14):
  `Ge A Ber mve Kie via` → `via_convoy=True`
- **`::style`** — rendering hint; currently implemented: `::error` draws a red
  ring around the order's ORIGIN field (used by the FAIL-REPORT to mark the
  orders that diverge between engines)
- **`# ...`** — line comments are allowed at the end of ANY line (map, edges,
  units, orders, pragmas, title, desc)
### Expected result markers

Markers at the end of an order line define the expected result used by `tests/test_dwex_examples.py`:

| Marker | Meaning |
|--------|---------|
| `!` | order fails / does not succeed |
| `>` | unit is dislodged |
| `!>` | order fails and unit is dislodged |

No marker means success/no dislodgement unless the engine model leaves success as `None` for successful orders.

## `units {}`

Use `units {}` for diagrams or setup positions without a corresponding order:

```text
units {
  Fr A Par
  En F NTH
}
```

Most examples use `orders {}` only, because orders also imply unit positions.

## `switches {}`

Switches set scenario-local resolver options. Values are parsed as strings/bools/numbers according to the DWEX parser and then passed into the model layer.

```text
switches {
  convoy_routing_engine: fixed:Lon-NTH-Bel
  self_cut_ok: false
}
```

Only use switches needed by the scenario; defaults should stay implicit.

## `pattfields {}`

Expected pattfields are listed one per line:

```text
pattfields {
  Tyr
}
```

These are included in the expected `ConflictResolution`.

## `pragmas {}`

Pragmas affect rendering, not conflict resolution.

```text
pragmas {
  no-mid-arrows
  field-jitter(0.05)
  layout-fill
}
```

Currently used pragmas:

| Pragma | Effect |
|--------|--------|
| `no-mid-arrows` | Suppress midpoint arrows on support/convoy curves |
| `field-jitter(<float>)` | Tune random-looking deterministic field label/unit offset |
| `layout-fill` | Stretch the node coordinates over the whole figure area, then a bounded Lloyd relaxation (Voronoi-cell centroids) evens out dense clusters; the neighborhood structure is preserved. Best for dense boards (>15 nodes) |

## Generation and tests

From `project/`:

```bash
make examples         # render all PNGs and rebuild doc/EXAMPLES.md
make examples-check   # run every .dwex as a regression test
```

Source files live in `doc/examples/dwex/`. Commit `.dwex`, regenerated `.png`, and regenerated `doc/EXAMPLES.md` together.
