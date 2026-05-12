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

See `../../../docs/superpowers/specs/2026-05-12-dipworkpy-comprehensive-design.md`
section 6.
