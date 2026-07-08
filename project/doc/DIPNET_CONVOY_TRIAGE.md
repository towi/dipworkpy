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
