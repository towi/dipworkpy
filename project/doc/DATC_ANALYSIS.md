# DATC Bug Analysis (Phase P7)

This document analyses the three DATC tests historically documented as failing
(in `CLAUDE.md` and the original spec): **6.D.2**, **6.D.3**, and **6.F.1**.

For each case the actual current output of `conflict_game` is compared with the
expected output in `tests/test_conflict_datc.py`. The DATC reference text is
extracted from `testdata/datc-v3/DATC_v3_2.html` (or `DATC_v3_0.html` when the
case has been renumbered between versions).

The conventions are:

- **bug** = algorithm produces objectively wrong results; fix the algorithm.
- **variant** = the test expects a different valid interpretation of the rules
  from what the algorithm produces; gate behind a `Switches` flag and keep
  the current default.

---

## 6.D.2 — Move with Support

**Status: ALREADY PASSES.**

Re-running the test suite at the start of P7 showed only **two** failing DATC
cases (6.D.3 and 6.F.1). 6.D.2 is green in the current code base; the
`CLAUDE.md` note about three failures is stale (P3 already mentioned only two).

Test orders:

```
Au A Vie mve Tri        # supported attack from Vie -> Tri
Au A Tyr msup Vie       # support for Vie's attack
It A Tri hld            # defender holds Tri, no support -> dislodged
```

Expected outcome: Vie moves to Tri, Tri unit dislodged, pattfields = {}. The
engine produces exactly this. No code change required.

---

## 6.D.3 — A Move Cuts Support on Move

**DATC reference (v3.2, section 6.D.3):**

> THE SIMPLEST SUPPORT ON MOVE CUT
> Austria:
> - F Adriatic Sea Supports A Trieste - Venice (cut)
> - A Trieste - Venice (fails)
>
> Italy:
> - A Venice Holds (stands)
> - F Ionian Sea - Adriatic Sea (fails)

The DipworkPy test mirrors the same topology with different province codes
(Vie/Tri/Tyr/Ven). All four moves bounce, no dislodgements, the message that
DATC actually verifies is `cut / fails / stands / fails` — the success/fail
flags only.

**Engine output today (orders):**

| Order              | succeeds | dislodged |
|--------------------|----------|-----------|
| Au A Vie mve Tri   | False    | -         |
| Au A Tyr msup Vie  | False    | -         |
| It A Tri hld Tri   | True     | -         |
| It A Ven mve Tyr   | False    | -         |

That is exactly what DATC asks for. Order-level resolution is **correct**.

**Where the test fails:** the project-specific `pattfields` set. The test
expects `{Tri, Tyr}` (destinations of the two bounced moves); the engine
returns `{}`.

**Phase:** writer (in `conflict_game.py`), not k2/k3. The conflict resolution
itself is right; only the post-processing of pattfields disagrees.

**Why the formula produces `{}` today**

In `conflict_game.writer`:

```python
pattfields = (efields | ufields) - sfields - (hfields - efields)
```

- `ufields` = {Tri, Tyr}  (destinations of umove orders)
- `hfields` = {Tri, Tyr}  (Tri holds; Tyr's msupport collapsed to `none` after cut)
- `efields` = {}, `sfields` = {}

→ `({Tri, Tyr}) - {} - ({Tri, Tyr}) = {}`.

The current rule subtracts any hold-or-support field unless it is empty. That
matches the existing core test `test_conflict_game_02` (single bounce on an
occupied hold target, pattfields=`{}`) and `test_conflict_game_patt_01`
(two bounces on an empty target, pattfields=`{Vie}`).

**Diff with the DATC test expectation**

The 6.D.3 expectation treats *any* destination of a bounced move as a
pattfield, regardless of whether the destination is currently occupied. That
directly contradicts `test_conflict_game_02` which is structurally identical
to 6.D.3 (one attacker bouncing on an occupied hold) yet expects `set()`.

**Verdict: VARIANT.**

The two expectations are mutually inconsistent under a single rule. The
DATC-stricter behavior is gated behind a new `Switches` flag,
`pattfields_include_failed_dests`. Default `False` (preserves
`test_conflict_game_02` and the rest of the suite). The DATC tests flip the
switch to `True` to obtain `{Tri, Tyr}`.

**Code change**

- New switch in `dipworkpy/model.py` (`Switches.pattfields_include_failed_dests`)
  with a `_ri_pattfields_include_failed_dests` docstring constant.
- `conflict_game.writer` reads the switch from the world and adds `ufields`
  back into the result set when the switch is True.
- The DATC test passes `Switches(pattfields_include_failed_dests=True)` via
  the `Situation`.

---

## 6.F.1 — Beleaguered Garrison

**DATC reference (v3 versions split the number):**

DATC v3.2's 6.F.1 is "No convoy in coastal provinces" and is unrelated. The
DipworkPy-internal numbering reuses 6.F.1 for *Beleaguered Garrison*, which in
DATC v3.2 lives in section 6.E (with the closest direct match being the family
of *Beleaguered Garrison* test cases in 6.E.7 / 6.E.8 etc., all of which
verify that the holding unit is **not dislodged**, no more and no less).

The DATC consensus on the scenario:

> When a unit in a province is attacked by two or more units from different
> sources, each individually unable to dislodge it, the unit stands and the
> attackers all bounce.

**Engine output today (orders):**

| Order              | succeeds | dislodged |
|--------------------|----------|-----------|
| Ge A Mun mve Ber   | False    | -         |
| Ge A Pru mve Ber   | False    | -         |
| Ru A War mve Ber   | False    | -         |
| Ru A Ber hld Ber   | True     | -         |

Again: **order-level resolution is exactly right** (three attackers bounce,
the Russian unit stands and is not dislodged). The DATC criterion is met.

**Where the test fails:** the pattfield set. The test expects `{Ber}`; the
engine returns `{}` for the same reason as 6.D.3:

- `ufields` = {Ber} (three umoves all targeting Ber)
- `hfields` = {Ber} (Ru A Ber hld)
- formula: `{Ber} - {} - {Ber} = {}`

**Phase:** writer, same `pattfields` computation.

**Diff with the DATC test expectation**

The 6.F.1 expectation matches 6.D.3's: destinations of bounced moves enter
`pattfields` even when occupied by a holding unit. Same inconsistency with
`test_conflict_game_02`.

**Verdict: VARIANT.**

Same fix as 6.D.3: gated behind `pattfields_include_failed_dests`. The DATC
test sets the switch to `True` to obtain `{Ber}`.

---

## Summary

| Case  | Real issue?             | Verdict       | Action                                |
|-------|-------------------------|---------------|---------------------------------------|
| 6.D.2 | No — already passes     | n/a           | none                                  |
| 6.D.3 | Pattfields set differs  | variant       | switch `pattfields_include_failed_dests` |
| 6.F.1 | Pattfields set differs  | variant       | switch `pattfields_include_failed_dests` |

The conflict resolution algorithm itself is correct for all three cases. The
historical "DATC failure" tag was always about a project-specific decision on
how to record bounced destinations in the `pattfields` output set. The
switch makes both interpretations available without forcing other passing
tests to be rewritten.

**Note on `test_conflict_game_02`:** This test (single attacker bouncing on
an occupied hold target, `pattfields=set()`) is structurally identical to a
single-move slice of 6.D.3, but expects the opposite pattfield outcome. It is
preserved as-is; the switch separates the two interpretations.

---

## Resolution (2026-09-09)

**Resolved by the genuine-Patt rule per Gilgamesch C.2.2 / C.2.3.1 / C.3.1.3.2.**
The `pattfields_include_failed_dests` switch has been **deleted**. The writer
now collects the standoff marks (`t_field.patt`) that the eval phases set:

- a pattfield is a field with a **genuine movement-phase standoff** — a
  beleaguered garrison / multi-attacker tie (C.2.2) or a head-to-head tie
  (C.2.3.1);
- **single-attacker bounces are NOT patt** (C.2.1): their destinations never
  enter `pattfields` beyond being occupied/contested.

Consequences for the cases above:

- **6.D.3**: both bounced destinations (Tri, Tyr) are single-attacker
  bounces — the test expectation is corrected to `pattfields=set()`. The old
  `{Tri, Tyr}` encoded the DATC-strict bounced-destinations convention, which
  Gilgamesch rejects. The order-level results were always correct.
- **6.F.1**: the beleaguered garrison is a genuine C.2.2 standoff —
  `pattfields={Ber}` now holds under the single rule, with no switch.
- **`test_conflict_game_02`**: still `set()` (single-attacker bounce) — the
  structural conflict with 6.D.3 is gone because both now follow the same
  rule.
