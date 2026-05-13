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

| Order   | Visual                                                                                |
|---------|---------------------------------------------------------------------------------------|
| `mve`   | filled triangle arrowhead (matplotlib `-\|>`)                                         |
| `msup`  | open V arrowhead (`->`) at the end of a Bézier curve through the supported unit       |
| `hsup`  | square marker at the held unit                                                        |
| `con`   | open bracket (`-[`, dock/anchor) at the end of a Bézier curve from the convoyer through the convoyed army's start to its destination |

In addition to the end-shape, support and convoy orders (`hsup` / `msup` / `con`) carry a small filled-triangle arrow at the curve's midpoint to signal direction at a glance. The midpoint arrow can be suppressed per example via the `no-mid-arrows` pragma (see below).

### Axis 2: line style → outcome

| Line     | Meaning                                       |
|----------|-----------------------------------------------|
| solid    | success — order had its intended effect       |
| dashed   | failure (corresponds to `!` in the DDL source) |

### Axis 3: color → nation

The same color is used for the unit badge AND every order issued by that nation. A red filled-triangle on a solid arrow means "Austria's army successfully moved." A red dashed filled-triangle means "Austria attempted to move; it bounced or was invalid."

| Nation                | Color                  | Original convention |
|-----------------------|------------------------|---------------------|
| Au — Austria-Hungary  | dark red `#8b1a1a`     | red                 |
| En — England          | dark blue `#3a5ba0`    | dark blue           |
| Fr — France           | dark cyan `#0e7490`    | light blue          |
| Ge — Germany          | warm brown `#6d4c41`   | black               |
| It — Italy            | dark green `#1b5e20`   | green               |
| Ru — Russia           | tan `#c8a878`          | white               |
| Tu — Turkey           | orange `#e67e22`       | yellow              |
| Xx — neutral / empty  | grey `#888888`         | (none)              |

The original Diplomacy board palette had several colours that don't read well on a printed/rendered page: pure red is a visual emergency signal, pure white disappears on white paper, pure yellow lacks contrast, and pure black is heavier than the surrounding linework. Each was shifted toward a darker / warmer / more saturated cousin while staying in the same hue family.

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

Field positions in the rendered PNGs are jittered by up to 20 % per axis (deterministic — same field name → same offset, so PNGs are stable in git). Examples authored on a strict grid render as gently scattered nodes rather than as straight rows and columns; the structural relations stay intact while the diagram looks less artificial.

---

## Pragmas

A `pragmas { ... }` block in a `.dwex` source toggles rendering options. Each line in the block is a single kebab-case identifier. Currently understood:

| Pragma           | Effect                                                                 |
|------------------|------------------------------------------------------------------------|
| `no-mid-arrows`  | Suppress the midpoint direction arrow on `hsup` / `msup` / `con` paths. Default: midpoint arrows enabled. |

Example (`05_support_move.dwex`):

```
pragmas {
  no-mid-arrows
}
```

Pragmas affect rendering only — they do not change the parsed `Situation` or the expected `ConflictResolution`, so the parametrized regression test (`tests/test_dwex_examples.py`) is unaffected by adding or removing them.

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
