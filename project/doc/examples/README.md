# DDL Examples

Each `.dwex` file is a single text source that yields four artefacts:

- a sibling `.png` (visualization rendered by matplotlib)
- a `Situation` for `conflict_game()` to execute
- a `ConflictResolution` expectation, driven by `!` (failed) and `>` (dislodged) markers in the source
- an inline `MapDefinition` so the example is self-contained, no external map needed

The numbered examples in this directory cover every order type and outcome shape the conflict engine produces. Each example also doubles as a regression test (`tests/test_dwex_examples.py`).

---

## Visual conventions — orthogonal system {#orthogonal-visual-conventions}

The renderer uses three independent visual axes. Each axis communicates exactly one piece of information; you can read any one axis without consulting the others.

### Axis 1: shape → order type

| Order   | Visual                                                                   |
|---------|--------------------------------------------------------------------------|
| `mve`   | filled triangle arrowhead (matplotlib `-\|>`)                            |
| `msup`  | open V arrowhead (`->`) at the end of a Bézier curve through the supported unit |
| `hsup`  | square marker at the held unit                                           |
| `con`   | hexagon at the convoyer — *reserved, not yet rendered*                   |

### Axis 2: line style → outcome

| Line     | Meaning                                       |
|----------|-----------------------------------------------|
| solid    | success — order had its intended effect       |
| dashed   | failure (corresponds to `!` in the DDL source) |

### Axis 3: color → nation

The same color is used for the unit badge AND every order issued by that nation. A red filled-triangle on a solid arrow means "Austria's army successfully moved." A red dashed filled-triangle means "Austria attempted to move; it bounced or was invalid."

| Nation         | Color                |
|----------------|----------------------|
| Au — Austria   | red `#E84545`        |
| En — England   | blue `#3A5BA0`       |
| Fr — France    | light blue `#79B8E0` |
| Ge — Germany   | dark grey `#444444`  |
| It — Italy     | green `#3DA34D`      |
| Ru — Russia    | tan `#c8a878`        |
| Tu — Turkey    | yellow `#F2C94C`     |
| Xx — neutral   | grey `#888888`       |

(Russia is traditionally rendered white in Diplomacy; bumped to tan here so it stays visible on a white page.)

### Reading examples

Combining the three axes:

- *Red, solid, filled-triangle arrow Vie → Mun:* Austria's army successfully moved Vienna to Munich.
- *Red, dashed, filled-triangle arrow Vie → Mun:* Austria's move bounced or was invalid; the unit stayed in Vie.
- *Dark grey, solid Bézier with open-V tip ending at Mun:* a German support-move into Mun — the curve passes through the supported unit's start field.
- *Dark grey, dashed Bézier:* that support was cut.
- *Blue square marker at Lon, with a blue line back to Wal:* an English hold-support on London from a unit in Wales.

### Background elements

| Element            | Style                                              |
|--------------------|----------------------------------------------------|
| Inland field       | tan circle (`LA` / `L`)                            |
| Coastal field      | sand circle (`LCB` / `LC` / `LCA` / `LCF`)         |
| Sea field          | pale blue circle (`O`)                             |
| Off-map / impass.  | grey circle (`COL`)                                |
| Adjacency edge     | dotted light grey, lw 0.9 — receded so order arrows stand out |

The unit badge is a small `boxstyle="round"` rectangle in the nation color, centred on the field, with white text `"<utype>:<nation>"` (e.g. `A:Au`, `F:En`).

---

## Render / validate

```bash
cd project

# Render every .dwex in this directory to a sibling .png + rebuild EXAMPLES.md
make examples

# Run the parametrized regression test (every .dwex is asserted against conflict_game)
make examples-check

# Or invoke the CLI directly
uv run python -m dipworkpy.tools.dwex render doc/examples/dwex/01_basic_hold.dwex
uv run python -m dipworkpy.tools.dwex validate doc/examples/dwex/01_basic_hold.dwex
uv run python -m dipworkpy.tools.dwex render-all doc/examples/dwex
```

## DSL reference

The `.dwex` grammar is described in section 6 of the comprehensive design spec at `../../../docs/superpowers/specs/2026-05-12-dipworkpy-comprehensive-design.md`. The renderer lives at `../../dipworkpy/tools/dwex/render_png.py`; the parser at `lang.py` in the same directory.
