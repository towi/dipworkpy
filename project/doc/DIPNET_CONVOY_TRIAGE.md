# DipNet post-geography-wiring FAIL triage (Task 9)

Triage of every FAIL produced by the geography-aware DipNet evaluator on the
100-game sample of `standard_no_press.jsonl`. Each FAIL is classified into
exactly one bucket:

- **A — engine bug**: the dataset is right and the resolver was wrong. Fixed
  here with a pinned regression test.
- **B — VIA-intent loss**: `mappings.py` silently drops DipNet's ` VIA`
  suffix (GEO-010 is deferred; `Order` has no `via_convoy` field). A move that
  DipNet resolves as "no convoy" reaches the engine as a plain (usually
  non-adjacent, therefore invalid) land move. Documented, **not** fixed here.
- **C — dataset/mapping artifact**: the adjudication the engine cares about is
  correct; the diff comes from a mapping/representation gap (the `con` mapping
  drops the convoy destination; a con/support order in a failed convoy chain
  reports success where DipNet reports "no convoy"). Documented, not fixed.

## Result

| Sample | Before Task 9 | After Task 9 |
| --- | --- | --- |
| 100 games (1602 cases) | 1561 PASS / 41 FAIL / 0 ERROR | **1595 PASS / 7 FAIL / 0 ERROR** |
| 1000 games (16876 cases) | — | **16739 PASS / 137 FAIL / 0 ERROR** |

Bucket counts on the 100-game FAIL set (41 total):

| Bucket | Count | Disposition |
| --- | --- | --- |
| A — engine bug (fixed, k1) | 31 | convoyer dislodged by a non-winning attack |
| A — engine bug (fixed, k4) | 3 | self-dislodgement of a returning head-to-head loser |
| B — VIA-intent loss | 3 | sized follow-up (GEO-010), see below |
| C — dataset/mapping artifact | 4 | documented, no engine change |

Every remaining FAIL (7 on the 100-game sample, 137 on the 1000-game sample)
is a documented bucket B or C case. On the 1000-game sample **100% of failing
phases contain a ` VIA` order** — there is no residual non-VIA/non-convoy
failure class.

## Root causes fixed (bucket A)

### 1. k1 resolved the convoy-attack conflict at the wrong field (31 cases)

`eval_k1.k1_evaluation` marked convoyers `fcategory==1` and their
attackers/supporters `category==1`, then called `resolve_conflict_at_field`
on the **`category==1`** fields — the attackers. k2 and k4 instead resolve at
their `fcategory==N` (contested) fields. An attacker's own field is
uncontested, so `resolve_conflict_at_field` never reassigned the attacker's
`succeeds`, which stayed at the `t_field` default `True`. The subsequent
"evaluate dislodgements of convoyers" loop then demoted **every** convoyer
that any unit moved onto — regardless of the convoyer's defensive strength or
hold-support. A convoying fleet was dislodged by an equal-strength (even
unsupported) attack that should merely bounce.

- **Repro (minimal):** `En A Lon mve Nor`, `En F NTH con Lon`,
  `Ge F Den mve NTH` → engine dislodged NTH (1 vs 1); correct outcome is Den
  bounces, NTH survives, Lon reaches Nor.
- **Fix:** `eval_k1.py` — resolve at `f.fcategory == 1` (the convoyers), matching k2/k4.
- **Tests:** `tests/test_conflict_convoy_dislodge.py` (unsupported attack
  bounces / supported attack still dislodges); the pre-existing
  `xfail` on `test_CV05_convoy_survives_equal_attack` — which documented this
  exact limitation — was removed (it now passes). CV-04's inline map was
  missing the `MID--NTH` border, so its "supported" attack was actually
  unsupported and only "worked" via this bug; the border was added so the
  example demonstrates a genuine dislodgement per its own description.
- **Corroboration:** `make test-stpsyr-full` improved 73→77 PASS; the
  newly-passing cases are the DATC convoy set ("An attacked convoy is not
  disrupted", "A beleaguered convoy is not disrupted", "Dislodged convoy does
  not cut support", …).

### 2. k4 did not re-resolve a bounced head-to-head loser's field (3 cases)

In a head-to-head (`Fr A Kie mve Ber` ↔ `Au A Ber mve Kie`) the border loser
is resolved in k3 while it is still a departing mover (`defensive_strength`
ignored, `defval==0`), so a third unit moving onto that field can win it —
including a **same-nation** unit, which no-self-dislodgement forbids. When the
loser bounces back it becomes `umove` but keeps `fcategory==3`, so k4 (which
only marked `fcategory==0` destinations) never re-resolved the field, and the
self-dislodge guard (which needs `defensive_strength>0`) never ran.

- **Repro (minimal):** head-to-head `Fr Kie↔Au Ber`, plus `Fr F HEL mve Kie`
  (supported by `Fr A Ruh`, str 2). `Fr A Kie` bounces at Ber and returns;
  engine let `Fr F HEL` dislodge its own returning `Fr A Kie`.
- **Fix:** `eval_k4.py` — also re-resolve a destination field when it now
  holds a bounced move (`order == umove`).
- **Test:** `tests/test_conflict_chain_characterization.py::test_no_self_dislodgement_when_head_to_head_loser_returns`.
- **Dataset corroboration:** in all three cases DipNet flags the enabling
  support order `void` (supporting the dislodgement of an own unit).

## Per-case triage table (100-game sample)

`diffing orders` lists the orders that differed *before* the fixes (the
signature of the failure). Diagnosis is one line.

| case_id | bucket | diffing orders | one-line diagnosis |
| --- | --- | --- | --- |
| `0Fl3BreFivkwKWvd_F1905M` | A (fixed: k1) | Ge F ENG mve Bre; Ge F Por mve MID; It F MID con Spa | convoyer dislodged by an attack that does not win its field. |
| `CRbbNicSK5Jc-qmb_S1904M` | A (fixed: k1) | It F ION con Tun; Tu F EAS mve ION | convoyer dislodged by an attack that does not win its field. |
| `CRbbNicSK5Jc-qmb_F1904M` | A (fixed: k1) | It A Tun mve Gre; It F ION con Tun; Tu F Gre mve Bul; Tu F EAS mve ION | convoyer dislodged by an attack that does not win its field. |
| `CRbbNicSK5Jc-qmb_S1907M` | A (fixed: k1) | It F Gre mve AEG; It F ION con Apu; Tu F AEG mve ION; Tu F Smy mve Syr; Tu A Con mve Smy | convoyer dislodged by an attack that does not win its field. |
| `CRbbNicSK5Jc-qmb_S1908M` | A (fixed: k1) | Fr A Pic mve Lon; Fr F ENG con Pic; Ge F NTH mve ENG | convoyer dislodged by an attack that does not win its field. |
| `CRbbNicSK5Jc-qmb_S1909M` | A (fixed: k1) | It F ION con Apu; It F EAS con Apu; Tu F AEG mve ION; Tu F Syr mve EAS | convoyer dislodged by an attack that does not win its field. |
| `CRbbNicSK5Jc-qmb_F1914M` | A (fixed: k1) | Fr F NTH con Edi; Ge F SKA mve NTH; Ge A Hol msup Mun | convoyer dislodged by an attack that does not win its field. |
| `ZSFmLzi-Th6lbpxy_S1903M` | A (fixed: k1) | Au A Bud mve Tri; Au A Tri mve Alb; Au F Alb mve ION; It A Tun mve Ven; It F ION con Tun | convoyer dislodged by an attack that does not win its field. |
| `p6m8jMuDPsM0dtUh_F1902M` | A (fixed: k1) | Au F Alb mve ION; It A Tun mve Apu; It F ION con Tun | convoyer dislodged by an attack that does not win its field. |
| `7uKSGh-EG86tfpyh_F1904M` | A (fixed: k1) | En A Yor mve Hol; En F NTH con Yor; Ge F SKA mve NTH | convoyer dislodged by an attack that does not win its field. |
| `omNMEctxL53gLSC0_F1906M` | C | It F ADR con Ven; It F ION con Ven | failed multi-fleet convoy (F EAS dislodged); engine reports surviving convoyers ADR/ION as success, DipNet marks them 'no convoy'. |
| `h9QEPT6s5-Fi1WrV_S1905M` | A (fixed: k1) | It F TYS mve ION; Tu A Bul mve Apu; Tu F ION con Bul | convoyer dislodged by an attack that does not win its field. |
| `h9QEPT6s5-Fi1WrV_F1910M` | A (fixed: k4) | Tu A Gal mve Boh; Tu A Rum mve Gal | head-to-head loser returns to its field; same-nation attacker dislodged it (no-self-dislodgement). |
| `cSaeUT4h0rewXGWH_S1908M` | C | En A Lon mve Hol | con mapping drops convoy DEST: fleet convoyed Lon->Bel but army wanted Lon->Hol; engine can't see mismatch, convoys Lon->Hol; DipNet 'no convoy'. |
| `hYYxzsZ9YfNbYcNp_F1906M` | A (fixed: k1) | Au A Apu mve Gre; Au F ION con Apu; Fr F TYS mve ION | convoyer dislodged by an attack that does not win its field. |
| `D619QzLd0FKfXi4m_S1904M` | C | Tu F Con msup Smy | failed convoy (F AEG dislodged); engine reports move-support F Con as success, DipNet marks it 'no convoy'. |
| `D619QzLd0FKfXi4m_S1914M` | A (fixed: k1) | Fr F Den mve BAS; Ge A Ber mve Liv; Ge F BAS con Ber | convoyer dislodged by an attack that does not win its field. |
| `kLq1Qi6MqjKKDd4G_F1917M` | A (fixed: k4) | Ru A Boh mve Tyr; Tu A Tyr mve Tri; Tu A Tri mve Bud | head-to-head loser returns to its field; same-nation attacker dislodged it (no-self-dislodgement). |
| `8Vv4RupS6oaY3W9-_S1902M` | A (fixed: k1) | En A Lon mve Pic; En F ENG con Lon; Fr F Bre mve ENG | convoyer dislodged by an attack that does not win its field. |
| `EWfQsnYLG5-OZLGU_F1902M` | A (fixed: k1) | Au F Gre mve ION; It A Apu mve Alb; It F ION con Apu | convoyer dislodged by an attack that does not win its field. |
| `EWfQsnYLG5-OZLGU_F1903M` | A (fixed: k1) | En A Lon mve Den; En F NTH con Lon; Ge F Kie mve Den; Ge F Hol mve NTH | convoyer dislodged by an attack that does not win its field. |
| `EWfQsnYLG5-OZLGU_S1904M` | A (fixed: k1) | En A Lon mve Nor; En F NTH con Lon; Ge F Hol mve NTH; Ge F Nor msup Hol | convoyer dislodged by an attack that does not win its field. |
| `EWfQsnYLG5-OZLGU_S1911M` | B | En F Edi msup Lpl; En F NTH con Lon; Ge F HEL mve NTH; It F Yor mve NTH | A Hol-Edi VIA (no convoy): dropped VIA -> invalid move cuts Edi's msup, cascading so Lpl can't dislodge It F Yor. |
| `qispC8HwumqyWTWM_F1904M` | A (fixed: k1) | En F Lon mve ENG; Fr A Pic mve Wal; Fr F ENG con Pic | convoyer dislodged by an attack that does not win its field. |
| `qispC8HwumqyWTWM_S1905M` | A (fixed: k1) | Au A Ven mve Apu; It F ADR mve ION; Tu F ION con Gre | convoyer dislodged by an attack that does not win its field. |
| `gIFm7p0bIuoOIz5g_S1902M` | A (fixed: k1) | En F NTH con Edi; Ge F Den mve NTH | convoyer dislodged by an attack that does not win its field. |
| `UGAB0Ijkqna4CE7y_S1904M` | A (fixed: k1) | En F Lpl mve Wal; En F Lon mve ENG; Fr F ENG con Bre | convoyer dislodged by an attack that does not win its field. |
| `UGAB0Ijkqna4CE7y_F1913M` | A (fixed: k1) | Fr F ION con Rom; It A Rom mve Alb; Tu F ADR mve ION | convoyer dislodged by an attack that does not win its field. |
| `15hanpsPjF23ncTe_F1910M` | A (fixed: k1) | Au F Pic mve ENG; En F ENG mve MID; En F IRI mve Lpl; En F NWS mve NAT; It F MID con Tus; It F NAT con Tus | convoyer dislodged by an attack that does not win its field. |
| `L8_VrUE-vy_KDLSv_F1902M` | A (fixed: k1) | En F NTH con Yor; Ge F Den mve NTH | convoyer dislodged by an attack that does not win its field. |
| `v08CT15R64vUdi9I_S1903M` | A (fixed: k1) | En F SKA mve NTH; Ge A Den mve Edi; Ge F NTH con Den | convoyer dislodged by an attack that does not win its field. |
| `8QrJVtFLhrudJBbO_S1909M` | A (fixed: k1) | En A Edi hld; En F Lon mve NTH; Ge A Bel mve Edi; Ge F NTH con Bel | convoyer dislodged by an attack that does not win its field (Edi-dislodge is a knock-on). |
| `yCOKdNHDFvK7BDp8_F1904M` | A (fixed: k1) | En F NTH con Lon; Ge F Den mve NTH | convoyer dislodged by an attack that does not win its field. |
| `yCOKdNHDFvK7BDp8_F1911M` | A (fixed: k1) | Ge A Bel mve Yor; Ge F NTH con Bel; It F Edi mve NTH | convoyer dislodged by an attack that does not win its field. |
| `GiCoWAei4QOEAPqB_S1905M` | C | Tu F AEG con Smy | failed convoy (F ION dislodged); engine reports surviving convoyer AEG as success, DipNet marks it 'no convoy'. |
| `5M65XaqXlieNDQVV_S1904M` | B | Au F ION mve Tun; Fr A Tun mve Gre | A Tun-Gre VIA (no convoy): dropped VIA -> invalid land move, def 0, dislodged by F ION; DipNet holds it full-strength. |
| `5M65XaqXlieNDQVV_S1907M` | A (fixed: k4) | Fr A Kie mve Ber; Fr F HEL mve Kie | head-to-head loser returns to its field; same-nation attacker dislodged it (no-self-dislodgement). |
| `EZl1DDW5twoaDS_C_S1906M` | A (fixed: k1) | En A Lon mve Pic; En F ENG con Lon; Fr F Bre mve ENG | convoyer dislodged by an attack that does not win its field. |
| `i2PD4EBRa0JFG3Tw_F1907M` | A (fixed: k1) | Fr A Bel mve Pic; Fr F Lon mve NTH; Ge A Nor mve Bel; Ge F NTH con Nor | convoyer dislodged by an attack that does not win its field (Bel-dislodge is a knock-on). |
| `mVPpqPmjYGo2gWmS_F1906M` | A (fixed: k1) | It F ADR mve ION; Tu A Alb mve Apu; Tu F ION con Alb | convoyer dislodged by an attack that does not win its field. |
| `BopmEdicW3FfiWAo_S1907M` | B | Fr A Pic hsup Bur | A Wal-Pic VIA (no convoy): dropped VIA -> invalid move still cuts Fr A Pic's hold-support. |

## Remaining FAILs (buckets B and C) — why they are not fixed here

### Bucket B — VIA-intent loss (3 cases)

`mappings.py` drops the ` VIA` suffix and `Order` has no `via_convoy` field
(GEO-010 deferred). A DipNet `A X - Y VIA` that resolves to "no convoy"
reaches the resolver as a plain move `A X mve Y`:

- When `X`–`Y` is non-adjacent, geography classifies it `holds_no_support`
  (defensive_strength 0), so a single attacker dislodges the army; DipNet
  holds it at full strength (`5M65XaqXlieNDQVV_S1904M`).
- The invalid move still **cuts support** at its nominal destination, whereas
  DipNet's "no convoy" move cuts nothing — cascading into unrelated diffs
  (`BopmEdicW3FfiWAo_S1907M`, `EWfQsnYLG5-OZLGU_S1911M`).

This is the known GEO-010 gap. Sizing from the wider sample below.

### Bucket C — dataset/mapping artifact (4 cases)

- **con destination dropped** (`cSaeUT4h0rewXGWH_S1908M`): the `con` mapping
  keys only on the convoyed unit's start field (per `NOTATION.md`), so a fleet
  convoying `Lon→Bel` is indistinguishable from one convoying `Lon→Hol`. When
  the army wants a different destination than the fleet offered, DipNet says
  "no convoy" but the engine happily convoys the army to where it wanted to
  go. Not representable in the current wire format.
- **con/support success in a failed convoy chain** (`omNMEctxL53gLSC0_F1906M`,
  `D619QzLd0FKfXi4m_S1904M`, `GiCoWAei4QOEAPqB_S1905M`): when a convoy chain
  collapses (a convoyer is dislodged), DipNet marks the *surviving* convoyers
  and the move-support "no convoy" (fail). The engine's adjudication is
  correct — the army fails to move and the dislodged convoyer is dislodged in
  both — but a `con`/`msup` order that is not itself dislodged reports
  `succeeds=None`. This is a reporting-convention difference, not a resolution
  error.

## Step 4 — wider sample (1000 games, parallel path)

Ran the parallel evaluator once post-wiring to exercise that path:

```
uv run python -m test_data_pipeline.run_dipnet_tests \
  --workers 8 --max-games 1000 ../testdata/diplomacy-research/standard_no_press.jsonl
→ 16739 PASS / 137 FAIL / 0 ERROR / 0 INCONCLUSIVE  (16876 cases)
```

Spot-check: the sequential run over the same 1000 games gives identical counts
(16739 / 137 / 0), confirming the parallel path is result-consistent (as
expected — `evaluate_test_case` is pure).

Failure-class check on the 1000-game FAIL set: **all 137 failing phases
contain a ` VIA` order**; 0 failing phases have neither a `VIA` nor a `con`
order. Diff-line signature counts (order-type, changed field):

```
104  (mve,  succeeds)      VIA-as-land-move + support-cut cascades
 49  (msup, succeeds)      spurious/absent support cuts from invalid VIA moves
 45  (mve,  dislodged)     def-0 invalid VIA moves + cascade dislodgements
 24  (con,  succeeds)      failed-convoy-chain reporting convention
 13  (hsup, succeeds)      spurious/absent hold-support cuts
  3  (other)               knock-on
```

No new bucket-A signature appeared in the wider sample: every remaining
failure is the bucket-B (VIA) / bucket-C (convoy-representation) family already
characterised above. The cheap bucket-A fixes were the two engine bugs above;
the remaining classes require the GEO-010 VIA follow-up and a wire-format
decision on convoy destination / failed-chain reporting, both out of scope for
this task.

## Follow-up sizing

- **GEO-010 / VIA (bucket B):** on the 100-game sample this is 3 of 41 FAILs;
  on the 1000-game sample **all 137 remaining FAILs (0.8% of cases) involve a
  VIA order**. Landing GEO-010 (a `via_convoy` flag on `Order`, so a
  no-convoy VIA move holds at full strength and does not cut support) is the
  single highest-leverage remaining correctness item for DipNet parity. See
  AGENTS.md roadmap.
- **Convoy wire-format (bucket C):** decide whether the `con` mapping should
  carry the convoy destination, and whether a con/support order in a failed
  chain should report `succeeds=False`. Both are representation choices, not
  resolver bugs.

---

# 2026-09-09 — Task 7 checkpoint: 100-game validation after VIA/swap/writer (REGRESSION)

Run: `make test-dipnet-quick` (`run_dipnet_tests --max-games 100`), HEAD `83be866`
(Tasks 1–6 + 4b/5b landed: via_convoy end-to-end, GEO-009 adjacency, swap,
writer con-reporting). This is a measurement/triage checkpoint — no engine
changes were made in Task 7.

## Numbers

| Sample (100 games, 1602 cases) | Baseline 2026-07-08 | 2026-09-09 (this run) |
| --- | --- | --- |
| PASS | 1595 | **1507** |
| FAIL | 7 | **95** |
| ERROR | 0 | **0** |
| INCONCLUSIVE (convoy) | 0 | **0** |
| INCONCLUSIVE (void) | 0 | **0** |

**REGRESSION: FAIL 7 → 95.** Reported as DONE_WITH_CONCERNS per the task
contract; every FAIL is individually triaged below.

## What did collapse: the VIA family (bucket B) — confirmed

All three historical bucket-B (VIA-intent loss) cases are resolved:

- `5M65XaqXlieNDQVV_S1904M` and `BopmEdicW3FfiWAo_S1907M` now **PASS**.
- `EWfQsnYLG5-OZLGU_S1911M` still FAILs, but its original VIA-cascade diff
  (`Edi msup Lpl` support-cut cascade) is gone; the only remaining diff is the
  new writer issue (class a below).

Across the whole 95-case FAIL set there is **no mve/hsup/msup cascade diff
left except the three documented residuals** — the M2 VIA/swap/GEO-009 work
holds up. The two historical bucket-C con-order cases where the Task 6 writer
fix was supposed to bite also improved: in `omNMEctxL53gLSC0_F1906M` and
`GiCoWAei4QOEAPqB_S1905M` the surviving convoyers of a broken chain now
correctly report `succeeds=False`, matching DipNet's `no convoy` (those
historical diffs are gone).

## What regressed: the Task 6 writer con-reporting condition (class a)

Commit `540913a` ("report con-order failure when convoy did not execute")
pinned the condition as *"army did not move via this convoy"*:

```python
executed = army is not None and army.order == t_order.cmove and army.succeeds
orr.succeeds = None if (executed and f.order == t_order.convoy) else False
```

DipNet's actual convention (verified against the raw dataset results) is:

| Situation (con order) | DipNet dataset result | Writer (got) |
| --- | --- | --- |
| convoy executed, army's move bounced at destination | `[]` → success | False |
| convoyer itself dislodged | `["dislodged"]` → succeeds unset | False |
| surviving convoyer of a broken chain | `["no convoy"]` → False | False ✓ |
| geo-invalid con (collapsed to hold) | (none in sample) | False |

So the fix overcorrects in two situations, and both are new FAILs:

- **R1 (88 cases):** the convoy executed fine (fleet undisturbed, route
  intact) but the convoyed army's move bounced at its destination. DipNet
  marks the con order a success; the writer reports `False`.
  Representative example `0Fl3BreFivkwKWvd_F1905M`: `A SPA - BRE VIA` with
  `F MAO C A SPA - BRE`; dataset results `A SPA: ["bounce"]`,
  `F MAO: []` — con succeeded.
- **R2 (5 cases, one mixed with R1):** the convoyer itself was dislodged.
  DipNet marks only `["dislodged"]` and leaves `succeeds` unset (default);
  the writer additionally reports `succeeds=False`.

In **every** R1/R2 case the rest of the adjudication matches DipNet exactly —
only the con order's `succeeds` flag differs. This is a reporting-layer bug
introduced by `540913a`, not a resolver bug and not a rule divergence. The
pinned writer tests (`test_writer_con_order_*`) cover executed / disrupted /
no-companion / geo-invalid, but miss exactly the two situations above
("convoy executed + army bounced" and "convoyer dislodged"). Suggested fix for
the controller: report `False` only when the fleet survived but the convoy
chain/route failed (or the con was geo-invalid); leave `succeeds` unset for an
executed convoy regardless of the army's bounce, and for a dislodged convoyer
(the `dislodged` flag carries that failure).

Diff-line signatures across all 95 FAILs (120 diff lines):

```
117  (con,  succeeds: exp None, got False)   R1/R2 writer over-reporting
  1  (mve,  succeeds: exp None, got False)   class b — VIA without convoy (h9QEP…)
  1  (mve,  succeeds: exp False, got None)   class c — con-dest dropped (cSaeUT…)
  1  (msup, succeeds: exp False, got None)   class c remnant — msup of failed convoy (D619…)
```

## Non-writer FAILs

- **`h9QEPT6s5-Fi1WrV_S1909M` — class (b), expected divergence.** Turkey
  ordered `A CON - BUL VIA`; no fleet convoyed (Con–Bul is a land border).
  DipNet resolves this as a plain adjacent move and reports success (`[]`);
  Gilgamesch's explicit-convoy semantics (B.3.2.14) require a working convoy
  for a `VIA` move, so the move fails. This case was previously a silent PASS
  (VIA dropped) and turned FAIL the moment M2 honored `via_convoy`
  end-to-end — it is the visible, expected cost of the honest B.3.2.14
  semantics, evidence of the documented Gilgamesch-vs-DipNet divergence, not
  a regression to fix.
- **`cSaeUT4h0rewXGWH_S1908M` — class (c), unchanged historical bucket C.**
  The `con` mapping drops the convoy destination (fleet convoyed Lon→Bel,
  army wanted Lon→Hol); DipNet says `no convoy`, engine convoys as ordered.
  Wire-format gap, unchanged since 2026-07-08.
- **`D619QzLd0FKfXi4m_S1904M` — class (c) remnant + R2.** The
  `Tu F Con msup Smy` diff remains (DipNet `["no convoy"]` on the move-support
  of a failed-convoy move, engine reports success): Task 6 covered `con`
  orders only, the msup reporting decision is still open. The AEG con diff in
  the same phase is the R2 writer issue.

## Per-FAIL triage table (95 cases)

Classes: **a (R1/R2)** = genuine engine bug (writer con-reporting, commit
`540913a`) → report for fix, NOT fixed in Task 7; **b** = Gilgamesch-vs-DipNet
rule-interpretation divergence → expected; **c** = dataset/mapping artifact.

| `cSaeUT4h0rewXGWH_S1908M` | c | En A Lon mve Hol | con mapping drops convoy destination (historical bucket C, wire-format gap): fleet convoyed Lon→Bel, army wanted Lon→Hol; DipNet 'no convoy'. |
| `h9QEPT6s5-Fi1WrV_S1909M` | b | Tu A Con mve Bul | VIA move `A CON - BUL VIA` with no convoyer on adjacent land route; DipNet resolves as plain move (success), Gilgamesch B.3.2.14 explicit-convoy semantics fail it. |
| `-joCH1jONGKS0wBT_F1906M` | a (R1) | Ge F ENG con Bel | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `0Fl3BreFivkwKWvd_F1905M` | a (R1) | It F MID con Spa | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `144oP_8-6uqCHwZM_F1905M` | a (R2) | Fr F ENG con Pic | R2 — convoyer dislodged; DipNet leaves con succeeds unset; writer: False (540913a). |
| `144oP_8-6uqCHwZM_F1910M` | a (R1) | En F BAS con Kie | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `15hanpsPjF23ncTe_F1902M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `15hanpsPjF23ncTe_F1903M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `15hanpsPjF23ncTe_F1910M` | a (R1) | It F MID con Tus; It F NAT con Tus; It F WMS con Tus; It F TYS con Tus | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `15hanpsPjF23ncTe_S1902M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `15hanpsPjF23ncTe_S1903M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `1IbGdARWCes1lsqm_F1902M` | a (R1) | Fr F ENG con Pic | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `5F6upbHF5NZlWuY__F1901M` | a (R1) | En F NTH con Yor | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `5F6upbHF5NZlWuY__S1902M` | a (R1) | Tu F BLA con Con | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `5JrcwYeklprQyQ9E_F1903M` | a (R1) | En F NTH con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `5JrcwYeklprQyQ9E_S1902M` | a (R1) | En F NTH con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `5M65XaqXlieNDQVV_F1905M` | a (R1) | Fr F WMS con Tun | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `7uKSGh-EG86tfpyh_F1902M` | a (R1) | En F NTH con Nor | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `7uKSGh-EG86tfpyh_F1903M` | a (R1) | Tu F BLA con Arm | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `7uKSGh-EG86tfpyh_F1905M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `8QrJVtFLhrudJBbO_F1902M` | a (R1) | It F EAS con Tun; It F ION con Tun | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `8QrJVtFLhrudJBbO_F1903M` | a (R1) | It F ION con Tun; It F EAS con Tun | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `8QrJVtFLhrudJBbO_F1908M` | a (R1) | Ge F NTH con Bel | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `8QrJVtFLhrudJBbO_S1903M` | a (R1) | It F EAS con Tun; It F ION con Tun | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `BKJDUpmRsGnikiLG_F1902M` | a (R1) | Tu F AEG con Con | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `BKJDUpmRsGnikiLG_F1907M` | a (R1) | Fr F NTH con Bel | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `BKJDUpmRsGnikiLG_F1908M` | a (R1) | Fr F NTH con Hol | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `BKJDUpmRsGnikiLG_S1907M` | a (R1) | Fr F NTH con Bel | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `CRbbNicSK5Jc-qmb_F1912M` | a (R1) | Tu F BLA con Ank | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `CRbbNicSK5Jc-qmb_F1914M` | a (R1) | Fr F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `CRbbNicSK5Jc-qmb_S1904M` | a (R1) | It F ION con Tun | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `CRbbNicSK5Jc-qmb_S1907M` | a (R1) | It F EAS con Apu; It F ION con Apu | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `CRbbNicSK5Jc-qmb_S1908M` | a (R1) | It F ION con Apu | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `CRbbNicSK5Jc-qmb_S1909M` | a (R1) | It F ION con Apu; It F EAS con Apu | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `D619QzLd0FKfXi4m_F1901M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `D619QzLd0FKfXi4m_F1903M` | a (R1) | Tu F AEG con Smy | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `D619QzLd0FKfXi4m_S1904M` | a (R2) | Tu F Con msup Smy; Tu F AEG con Smy | R2 (AEG con, exp None) + open bucket-C remnant: msup of failed-convoy move (exp False, got None; Task 6 covered con only). |
| `EWfQsnYLG5-OZLGU_S1910M` | a (R1) | Tu F BLA con Ank | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `EWfQsnYLG5-OZLGU_S1911M` | a (R1) | En F NTH con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `EZl1DDW5twoaDS_C_F1901M` | a (R1) | Tu F BLA con Con | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `EZl1DDW5twoaDS_C_F1903M` | a (R1) | Tu F BLA con Arm | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `GiCoWAei4QOEAPqB_S1902M` | a (R1) | Fr F WMS con Spa | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `GiCoWAei4QOEAPqB_S1905M` | a (R2) | Tu F ION con Smy | R2 — convoyer dislodged; DipNet leaves con succeeds unset; writer: False (540913a). |
| `HYc16KDWi8zHNlmn_F1901M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `HYc16KDWi8zHNlmn_S1902M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `HaJIleHsrwGvcRwO_S1905M` | a (R1) | En F ENG con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `HaJIleHsrwGvcRwO_S1906M` | a (R1) | En F ENG con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `L8_VrUE-vy_KDLSv_F1902M` | a (R1) | En F NTH con Yor; En F ENG con Yor | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `L8_VrUE-vy_KDLSv_S1905M` | a (R1) | Au F AEG con Gre; It F EAS con Gre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `NxMelzPAbZMYgrHY_F1902M` | a (R1) | It F EAS con Tun; It F ION con Tun | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `NxMelzPAbZMYgrHY_F1908M` | a (R2) | Fr F ENG con Bel | R2 — convoyer dislodged; DipNet leaves con succeeds unset; writer: False (540913a). |
| `NxMelzPAbZMYgrHY_F1909M` | a (R1) | Ru F BOT con Liv | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `NxMelzPAbZMYgrHY_S1903M` | a (R1) | It F EAS con Tun; It F ION con Tun | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `UGAB0Ijkqna4CE7y_S1904M` | a (R1) | Fr F ENG con Bre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `X9hvE_k6LbQrauYc_S1909M` | a (R1) | En F BAS con Kie | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `ZSFmLzi-Th6lbpxy_S1902M` | a (R1) | En F NTH con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `_-COKYjP7tTyg6wL_F1905M` | a (R1) | Fr F LYO con Mar; Fr F WMS con Mar; Fr F SKA con Den | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `_xZyPB0yRDQjRB4x_S1905M` | a (R1) | Fr F ENG con Bre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `cSaeUT4h0rewXGWH_F1901M` | a (R1) | En F ENG con Yor; En F NTH con Yor | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `gIFm7p0bIuoOIz5g_S1902M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `hYYxzsZ9YfNbYcNp_F1905M` | a (R1) | Fr F NTH con Bre; Fr F ENG con Bre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `i2PD4EBRa0JFG3Tw_S1904M` | a (R1) | Ru F BLA con Rum | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `kLq1Qi6MqjKKDd4G_F1906M` | a (R1) | Tu F BLA con Bul | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `kLq1Qi6MqjKKDd4G_S1904M` | a (R1) | Fr F ENG con Bre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `mVPpqPmjYGo2gWmS_F1902M` | a (R1) | Tu F BLA con Arm | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `mVPpqPmjYGo2gWmS_F1905M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `mVPpqPmjYGo2gWmS_F1906M` | a (R1) | En F ENG con Lon; En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `mVPpqPmjYGo2gWmS_S1903M` | a (R1) | Tu F BLA con Arm | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `mVPpqPmjYGo2gWmS_S1905M` | a (R1) | En F ENG con Lon; En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `mVPpqPmjYGo2gWmS_S1906M` | a (R1) | En F ENG con Lon; En F NTH con Edi; En F BAS con Den | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `mVPpqPmjYGo2gWmS_S1907M` | a (R1) | En F ENG con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `omNMEctxL53gLSC0_F1906M` | a (R1+R2) | Ge F ENG con Bre; It F EAS con Ven | mixed: ENG con — convoy executed, army bounced (dataset `[]`, R1); EAS con — convoyer dislodged (dataset `['dislodged']`, R2). Task-6 fix worked here: surviving ADR/ION now correctly report False (historical diff gone). |
| `omNMEctxL53gLSC0_S1909M` | a (R1) | Tu F BLA con Con | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `p6m8jMuDPsM0dtUh_F1910M` | a (R1) | Fr F ENG con Bre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `p6m8jMuDPsM0dtUh_S1902M` | a (R1) | En F NTH con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `p6m8jMuDPsM0dtUh_S1906M` | a (R1) | It F AEG con Gre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `p6m8jMuDPsM0dtUh_S1910M` | a (R1) | Fr F ION con Tun | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `qispC8HwumqyWTWM_F1903M` | a (R1) | Fr F ENG con Pic | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `qispC8HwumqyWTWM_S1902M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `qispC8HwumqyWTWM_S1903M` | a (R1) | Fr F ENG con Pic | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `qispC8HwumqyWTWM_S1905M` | a (R1) | Tu F ION con Gre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `qispC8HwumqyWTWM_S1914M` | a (R1) | Ru F ION con Gre | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `sdKZrT-i_BvEZsFU_F1903M` | a (R2) | Fr F ENG con Pic | R2 — convoyer dislodged; DipNet leaves con succeeds unset; writer: False (540913a). |
| `tBO2WYzXwQbv_wyg_F1901M` | a (R1) | It F ION con Apu | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `uixMfZorjeMHLaQw_F1902M` | a (R1) | Tu F BLA con Con | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `uixMfZorjeMHLaQw_F1904M` | a (R1) | Ge F NTH con Den; Tu F BLA con Con | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `uixMfZorjeMHLaQw_F1906M` | a (R1) | Ge F NTH con Hol | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `uixMfZorjeMHLaQw_S1904M` | a (R1) | Tu F BLA con Con | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `v08CT15R64vUdi9I_F1909M` | a (R1) | It F LYO con Tus | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `v08CT15R64vUdi9I_S1907M` | a (R1) | It F ION con Nap; It F EAS con Nap | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `yCOKdNHDFvK7BDp8_F1901M` | a (R1) | En F NTH con Edi | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `yCOKdNHDFvK7BDp8_F1902M` | a (R1) | En F NTH con Yor | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `yCOKdNHDFvK7BDp8_F1904M` | a (R1) | En F NTH con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `yCOKdNHDFvK7BDp8_S1905M` | a (R1) | En F ENG con Lon | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |
| `zmhBXDp3OIdfkVk9_F1906M` | a (R1) | Fr F TYS con Spa; Fr F WMS con Spa | R1 — convoy executed, army bounced elsewhere; DipNet: con success; writer: False (540913a). |

## Disposition

- The 93 class-a cases (88 R1 + 5 R2, one case mixed) are one single root
  cause: the `540913a` writer condition. One-line fix in
  `conflict_game.writer`, plus two pinned writer tests for the missing
  situations. **Not fixed here** (Task 7 is measurement only) — handed to the
  controller as the top follow-up; expected effect: FAIL 95 → ~3.
- The class-b case is the documented VIA divergence; count it as evidence.
- The class-c cases are the known wire-format gaps (con destination; failed-
  chain msup reporting), unchanged.
- Accounting: 90 previously-PASS cases newly FAIL (86 R1 + 3 R2 + 1 class b);
  2 previously-FAIL cases now PASS (`5M65XaqXlieNDQVV_S1904M`,
  `BopmEdicW3FfiWAo_S1907M`); 1595 − 90 + 2 = 1507 PASS. Consistent.

## 2026-09-09 — Fix landed: writer R1/R2 refined (2779bef)

The regression above was fixed the same day in `2779bef` ("con-order failure
only for surviving broken chains (DipNet R1/R2)"): a dislodged convoyer
reports `succeeds=None` (the `dislodged` flag carries the outcome), and a
surviving fleet of an intact chain whose army bounced at the destination
(engine state `umove`) reports `None` as well. `succeeds=False` now means
exactly DipNet's `no convoy`: a surviving fleet of a broken chain (army never
shipped, order `none`), a con without companion mve, or a geo-invalid con.

Post-fix 100-game run: **PASS 1599 (99.8%), FAIL 3, ERROR 0, INCONCLUSIVE 0**
(was 1507/95 pre-fix). All 93 class-a R1/R2 diffs are gone. The 3 remaining
FAILs are the documented non-con residuals:

| Case | Class | Diff |
| --- | --- | --- |
| `h9QEPT6s5-Fi1WrV_S1909M` | b (Gilgamesch-vs-DipNet) | `Tu A Con mve Bul` expected None, got False — B.3.2.14 explicit-convoy semantics fail a VIA move without convoyer on an adjacent land route; DipNet adjudicates it as a plain land move |
| `cSaeUT4h0rewXGWH_S1908M` | c (wire format) | `En A Lon mve Hol` expected False, got None — con-destination dropped in the wire mapping (known gap) |
| `D619QzLd0FKfXi4m_S1904M` | c (wire format) | msup of a failed convoy, expected False, got None (known gap) |

The two class-c residuals are the historical bucket-C wire-format items
(con destination; failed-chain msup reporting) — unchanged, tracked for the
data-pipeline backlog. The class-b case is expected evidence of the B.3.2.14
divergence, newly visible because via_convoy is honored (keep as documented
divergence, not a regression).

---

# 2026-09-09 — MISSION close-out: final validation of both samples (Task 14)

HEAD `7cf22c3` (all 13 implementation tasks of the "Conflicter correctness"
mission landed; `make check` fully green — core 7, DATC 25, graphs 12,
stpsyr-simple 3/3, integration demo, ruff/format/mypy clean). This section
closes the GEO-010/VIA work. Samples and commands:

```
make test-dipnet-quick                     # 100 games, 1602 cases
→ 1599 PASS / 3 FAIL / 0 ERROR / 0 INCONCLUSIVE  (99.8%)

uv run python -m test_data_pipeline.run_dipnet_tests \
  --workers 8 --max-games 1000 ../testdata/diplomacy-research/standard_no_press.jsonl
→ 16790 PASS / 86 FAIL / 0 ERROR / 0 INCONCLUSIVE  (99.5%, 16876 cases)
```

(The Makefile `test-dipnet-full` target runs all 33K games; the mission gate
is the 1000-game sample, matching the Task 9 baseline.)

## The pre-mission VIA family collapsed

Against the pre-mission baseline (Task 9 state, `314dad6`, re-measured today:
**16739 PASS / 137 FAIL**, identical to the recorded numbers):

| | before mission | after mission |
| --- | --- | --- |
| 1000 games (16876 cases) | 16739 / 137 | **16790 / 86** |
| of the 137 pre-mission FAIL cases | — | **76 now PASS**, 61 still FAIL |
| new FAILs (passed before, fail now) | — | **25** |

The pre-mission failure *class* — VIA-as-land-move with multi-order support-cut
cascades (104 mve/49 msup/45 dislodgement diff lines) — is **gone**: no current
FAIL shows that signature. The 61 still-failing ex-137 cases now fail with 1–2
single-flag diffs from the con-destination wire gap or the failed-convoy
support-reporting convention (families C1/C2 below) — i.e. they are bucket-C
residuals, not VIA-intent loss. The 25 new FAILs are all newly-visible
consequences of the (Gilgamesch-correct) B.3.2.14 implementation, triaged
below; none is an engine bug.

## 1000-game FAIL triage (86 cases, every case individually root-caused)

| Family | Class | Cases | One-line diagnosis |
| --- | --- | ---: | --- |
| C1 — con-dest mismatch | c (wire format) | 32 | raw `F X C A Y - Z` convoy destination ≠ the army's stated move dest; DipNet says 'no convoy'/voids the con, our dest-blind mapping either convoys the army anyway (changing bounces downstream) or demotes it to a stand that still cuts support (B.4.2.10 knock-on). Same gap as `cSaeUT4h`; includes one multi-con variant (`7vMwqXLvG2s2MysN_S1910M`: two cons with different destinations). |
| C2 — support of a failed convoyed move | c (reporting convention) | 29 | DipNet marks the msup/hsup backing a failed convoyed move `no convoy` (False); the engine leaves `succeeds` unset (the support was never cut — DATC-consistent). Same gap as `D619QzLd_S1904M`. |
| B1 — VIA move, no con order | b (Gilgamesch-vs-DipNet) | 17 | B.3.2.14 sentence 1: a flagged move is a convoy move; with no convoyer it stands with full defensive strength and no effect. DipNet instead resolves it as a plain land move. Includes `h9QEPT6s5-Fi1WrV_S1909M` (the documented 100-game residual) and knock-ons (`9jltG8kG1ziqpHGY_S1905M`: F Gre not dislodged; `mtjfOMBf5HA5C0Yq_F1904M`: F IRI bounces at the still-occupied Lpl). |
| C3 — supporter dislodged by a convoyed attack | c (reporting convention) | 5 | DipNet records only `['dislodged']` (succeeds unset) when a supporter is dislodged by a *convoyed* attack; the engine additionally reports `succeeds=False` (support cut by the dislodging attack, DATC-consistent). Positions identical. (`TPFTRCH2a15LeMxF_S1908M`, `FYYVuB2E7_vqnqVe_S1903M`, `3nrx13Lu-UJKg8nf_S1905M`, `11slj50Jauf59tP8_F1902M`, `sc0TipaHEPjx9Pqw_F1902M`.) |
| B3 — unflagged adjacent move + con order | b (Gilgamesch-vs-DipNet) | 2 | B.3.2.14 sentence 3 (GEO-009): an unflagged move to a directly adjacent field is a land move, convoy routes ignored → the con order reports not-executed (`False`); DipNet leaves the con's `succeeds` unset. (`LoiPYFIJZKP7ysev_F1917M` `F BLA C A CON - ANK`, `Ns_PFTfwd23yr0TM_F1907M` `F SKA C A SWE - DEN`.) |
| B2 — bounced convoyed attack cuts support | b (Gilgamesch-vs-DipNet) | 1 | A convoyed attack that bounces at its destination still cuts support there (standard rules; B.3.2.15's cut-immunity exception does not apply — the support targets the army's origin, not a necessary convoyer). DipNet does not cut. (`VEQUkSbvIL1sTxTz_S1911M`: engine cuts `Au A Bul msup Alb`, so `F Alb` bounces 1v1 and `Tu A Gre` is not dislodged; DipNet keeps the support, dislodges.) |

**Class (a) engine bugs: zero.** Every remaining FAIL is a documented
wire-format/reporting artifact (c) or a Gilgamesch-vs-DipNet divergence with the
engine on the Gilgamesch side (b). The 3 residuals on the 100-game sample are
consistent with this table: `h9QEPT6s5` (B1), `cSaeUT4h` (C1), `D619QzLd` (C2).

stpsyr gate (same run): **76 PASS / 16 FAIL / 0 ERROR** (of 92) — unchanged
from the post-Task-13 state; the 16 are the pre-existing coast/board-comparison
family plus test 32 (corpus itself marks the expectation non-DATC), see the
runner's triage note.

## Follow-ups filed

The C1/C2 wire-format items (con destination in the mapping; failed-chain
support reporting) and the class-b divergences are filed in `AGENTS.md`
(Known Gaps backlog, 2026-09-09) with exit criteria. None is an engine bug;
per the mission spec hierarchy Gilgamesch semantics win where they diverge
from DipNet.
