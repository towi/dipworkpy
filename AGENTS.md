# AGENTS.md — dipworkpy living plan & handoff

> **Scope of this file:** the living roadmap, DATC-compliance status, current handoff state,
> next tasks, known gaps, and the adversarial plan review log. The stable project reference
> (overview, pipeline, notation, commands, data structures) lives in `CLAUDE.md`.
>
> Re-verify git state before acting on the handoff; the architectural corrections below are stable.

## Roadmap (Future Priorities)

> Verified 2026-06-23; items 0-2 rewritten 2026-09-09 at mission close (see item 0).

0. **MISSION: Conflicter correctness — convoys, subfields, bugs — DONE (2026-09-09).** Plan (historical record, do not modify): `project/doc/plans/2026-09-09-conflicter-correctness.md` (14 tasks, TDD). All 13 implementation tasks landed at HEAD `7cf22c3` (25 commits after `314dad6`), Task 14 = final validation + this doc refresh. Results: subfield invariant test-enforced; `Order.via_convoy` end-to-end (GEO-010/Gilgamesch B.3.2.14, GEO-009 adjacency); convoy swap B.3.2.13; B.3.2.15 cut immunity + fn6 ambiguity fallback (three-pass k1, DATC 6.F.13–24 covered, divergences 6.F.18/6.F.21 documented); pattfields = genuine standoffs per C.3.1.3.2 with the switch deleted; writer con-reporting R1/R2 fixed; `$cnv` event + override warning; test_6_a_1 tightened; IX_3/IX_7 DATC mapping + switch tests. Gates: `make check` green, DipNet 100 games **1599/3 FAIL** (3 classified residuals), 1000 games **16790/86 FAIL** (137→86; every remaining FAIL triaged class b/c, zero engine bugs — see `project/doc/DIPNET_CONVOY_TRIAGE.md` final section), stpsyr 76/16 (triaged).
1. **Convoy paradox handling — DONE via MISSION Task 8 (supersedes the fixpoint framing).** The old framing ("k1 one-shot, needs a fixpoint") was wrong: Gilgamesch resolves the DATC v3.2 convoy-paradox family (canonical range 6.F.13–6.F.24) structurally — B.3.2.15 cut immunity (attack-supports only, literal text) + footnote-6 ambiguity fallback (all stand), as a bounded deterministic three-pass k1. Covered in `tests/test_convoy_paradox.py`. Documented divergences: 6.F.18 resolves all-stand per fn6 (Szykman-observable outcome differs), 6.F.21 matches the DATC-preferred result after re-derivation.
2. **Pattfields formula — DONE via MISSION Tasks 9–10.** Resolution phases now mark genuine standoffs on `t_field.patt` (C.2.2/C.2.3.1/C.3.1.3.2); `writer` collects `f.patt` and the old set formula plus `Switches.pattfields_include_failed_dests` are deleted. One rule satisfies 6.D.3 (expectation corrected to `set()`), 6.F.1, and `test_conflict_game_02` simultaneously.
3. **Retreat conflict resolution.** Only `retreat_options` enumeration exists (`geography/retreat.py`). Two retreating units choosing the same field (DATC 6.H.10–6.H.16) is its own mini conflict engine and is not yet scoped. DoD: spec of retreat-conflict inputs/outputs + DATC 6.H.* tests + interaction with `pattfields`.
4. **Winter adjustments: support-center counting + build/disband.** Requires SC ownership tracking, year/season state, build/disband orders, civil-disorder rules. DoD: (a) data model for SC ownership + season/year on `Situation`/result; (b) phase integration point after Retreats in the round orchestrator; (c) DATC build/disband/civil-disorder tests. Currently no data model, no phase integration, no tests — scope as a milestone, not a one-liner.
5. **DipNet triage + geography-aware evaluation — DONE (Task 9).** The evaluator now feeds `ConvoyGraph`/`order_geo_info` into the resolver and every FAIL on the 100-game sample is triaged (see `project/doc/DIPNET_CONVOY_TRIAGE.md`). Two engine bugs were fixed (k1 resolved convoy-attack conflicts at the attacker instead of the convoyer; k4 skipped re-resolving a bounced head-to-head loser's field, permitting self-dislodgement): 100 games went 1561→**1595 PASS / 7 FAIL / 0 ERROR**, and `test-stpsyr-full` 73→**77 PASS**. Remaining FAILs are all documented bucket B/C. **Sized follow-up — GEO-010 / VIA (bucket B):** `mappings.py` drops DipNet's ` VIA` suffix and `Order` has no `via_convoy` field, so a no-convoy VIA move reaches the resolver as a plain (often invalid) land move — it holds at defensive_strength 0 and spuriously cuts support. On the 1000-game sample **all 137 remaining FAILs (0.8%) involve a VIA order**; this is the single highest-leverage remaining DipNet-parity item. A residual bucket-C item: the `con` wire mapping drops the convoy destination, and con/support orders in a collapsed convoy chain report `succeeds=None` where DipNet reports "no convoy".
6. **(Superseded) Roadmap item 5 above is retained for the record only** — its GEO-010/VIA follow-up and 1595/7 + stpsyr-77 numbers predate the 2026-09-09 mission; see Roadmap #0 and Known Gaps ("DipNet evaluator not geography-aware") for the completed state.

## DATC Compliance (honest status)

"DATC 10/10" means **10 hand-picked cases** in `tests/test_conflict_datc.py`, not DATC v3.x compliance. The suite uses **DipworkPy-internal numbering** (see `tests/TEST_CASES_DATC.md`): 6.A basic, 6.B coast, 6.C circular, 6.D support, 6.E basic convoy, 6.F beleaguered, 6.G convoy paths, 6.H supports/dislodges, 6.I complex. **This differs from DATC v3.2 canonical**, where 6.E = Head-to-Head/Beleaguered and 6.F = Convoys (confirmed in `project/doc/DATC_ANALYSIS.md`).

Coverage gaps (internal numbering unless noted):

- **Convoy paradoxes** — COVERED (MISSION Task 8, 2026-09-09): DATC v3.2 convoy-paradox family (Pandin's, Szykman's, circular-disruption; canonical ≈6.F.13–6.F.24) is implemented per Gilgamesch semantics (B.3.2.15 cut immunity + fn6 all-stand ambiguity fallback, bounded three-pass k1) and pinned in `tests/test_convoy_paradox.py`. Documented divergences from DATC-preferred results: 6.F.18 (fn6 all-stand; the Szykman-observable outcome differs), 6.F.21 (after re-derivation the implementation matches the DATC-preferred result). See Roadmap #1.
- **Beleaguered garrison** — only internal 6.F.1 / 6.F.2 covered; further DATC v3.2 6.E variants absent.
- **Support cut by dislodged unit** — only internal 6.H.1 covered.
- **Retreats** — no retreat section at all (full retreat conflict resolution unimplemented; see Roadmap #3).
- `test_6_a_1` — TIGHTENED (MISSION Task 12): rewritten via `round_full`; geography rejects the illegal non-adjacent move, and the B.4.2.9 umove reports `succeeds=False`.
- `rule_interpretation_IX_3` / `rule_interpretation_IX_7` — MAPPED (MISSION Task 13): IX_3 ↔ DATC v3.2 6.D.10–6.D.14 + 6.D.20, IX_7 ↔ 6.E.4–6.E.6/6.E.12 (head-to-head = 6.E, not 6.C); tested across switch positions. Residual: IX_3 value 0 converges toward value-2 behaviour in k4, and IX_7 lacks `ge=0/le=2` validation (see Known Gaps).

## DATC Compliance (history)

All 10 hand-picked DATC cases pass (see honest scope above). Historical 6.D.2 / 6.D.3 / 6.F.1 status:

- **6.D.2** — was already passing at the start of the re-architecture session
- **6.D.3** / **6.F.1** — historically **masked, not structurally fixed** (gated behind `Switches.pattfields_include_failed_dests`, default off). RESOLVED 2026-09-09 (MISSION Tasks 9–10): genuine-standoff patt marking per C.3.1.3.2; the switch is deleted, the 6.D.3 expectation is corrected to `set()`, and one rule satisfies 6.D.3, 6.F.1, and `test_conflict_game_02` without gates.

See `project/doc/DATC_ANALYSIS.md` for the per-case write-up.

## Current Handoff State (verified 2026-09-09)

Branch: `feat/service-architecture-and-ddl`, **pushed** (at parity with `origin` at HEAD `7cf22c3` before the Task 14 doc commit; controller pushes). The MISSION "Conflicter correctness" (2026-09-09) is complete: all 13 implementation tasks + final validation landed; validation gates and the closing numbers are recorded in `project/doc/DIPNET_CONVOY_TRIAGE.md` (final section) and Roadmap #0 above. The historical log below is unchanged.

The ConvoyGraph integration is **committed and pushed**, not uncommitted:

- `62aa5e2 feat: route convoys through geography graph` — k1 uses the geography `ConvoyGraph` when supplied, restricts it to surviving convoyers after k1 dislodgement, falls back to legacy `convoy_routing_engine` only when no graph is supplied. Also adds `convoy_graph` to `t_world`, `conflict_game(...)`, `/conflict` API, and `round_full()`.
- `56e4b5a test: recover 21 pre-existing test failures` (three small fixes).
- `ceeaf36 docs: refresh status tables to match current implementation`.
- `cc6aff1 fix(api): default dev server boots the new app + endpoint test parity`.
- `c823daf feat(spec): close SYN-007 + GEO-007/008 diagnostics + clean dead markers`.
- `2049196 test: align OrderResult defaults to sparse + expand round_full coverage`.
- `2bb3f47 test(convoy): 8 CV-NN edge-case examples with diagrams + collector test`.

Earlier branch commits: `82ae863` (DWEX docs) → `c0b9281` (explicit geography map schema with field-local `borders`, `neighbor_order`, explicit `$convoy` marker independent of unit type `F`, `features`/`can_build`/`subfields`/`diversions`, retreat option service/API via right-hand-rule, split-coast tests Spa/Bul/Pet).

Working tree (no `project/` changes; noise only, non-exhaustive): `M .gitignore`, `M .idea/vcs.xml`, `?? .idea/db-forest-config.xml`, `?? .pi/`, plus `M CLAUDE.md` + `?? AGENTS.md` from this plan relocation.

Fresh verification (2026-09-09, mission close): `make check` fully green (core/DATC/graphs/stpsyr + ruff/format/mypy); see Roadmap #0 for the DipNet/stpsyr numbers. The earlier "66 passed / 99 passed, 1 skipped" figures were from 2026-05-19 and are stale.

## Suggested Next Tasks (ordered, with prerequisites)

1. **Clean working-tree noise + gitignore harness/IDE state.** Add `.pi/` and `.idea/` to `.gitignore`; decide on `.idea/db-forest-config.xml` (it may embed JDBC URLs/credentials — verify before ignoring). Keeps a stray `git add -A` from committing agent state. Prereq for any clean feature commit.
2. **Verify-or-dismiss the FastAPI/httpx test-client blocker (asserted in the now-superseded 2026-05-19 handoff; may be stale).** Prerequisite for #3 and #4. First reproduce: run the endpoint tests; if green, close this task and unblock #3/#4. If red, capture a `BLOCKER:` note here with (a) failing command, (b) error output, (c) root-cause category (missing dep / version pin / import path), (d) fix applied.
3. **Add API-level test for `POST /conflict` with `convoy_graph`.** Blocked on task 2. Also verifies the JSON round-trip of `ConvoyGraph` (tuple-keyed edges through Pydantic), which is currently untested end-to-end.
4. **Add/verify `POST /geography/retreat-options` API test.** Blocked on task 2.
5. **Run wider validation BEFORE the next commit, not after.** `make check`; `make examples-check` (defines: DWEX examples render + link-check); full geography/map/conflict subset. Required pass threshold and policy for the known `1 skipped` (`test_standard_map_fields_source.py`, which skips unless local `project/tests/standard.fields.txt` exists — decide CI provisioning).
6. **Document the standard-map JSON schema** in `project/doc/GEOGRAPHY.md`. Mark which fields are stable vs experimental (`features`, `can_build`, `subfields`, `diversions`, `$convoy`).
7. **Enforce `./pas/` confidentiality with a control, not a reminder.** Add a pre-commit/CI grep guard against `pas/` paths in tracked files, docs, and generated fixtures (EXAMPLES.md, DDL output). The rule is currently unenforced.
8. **Reconcile dual lockfiles.** Both `project/poetry.lock` and `project/uv.lock` exist; pick one canonical source of truth and remove/ignore the other to avoid reproducibility/security drift.

## Known Gaps (require implementation, not plan edits)

These surfaced in the 2026-06-23 adversarial plan review and cannot be resolved by editing this file. Each line ends with its exit criterion (`exit:`) or an open decision (`DECISION:`).

- **Convoy paradox fixpoint** — CLOSED (MISSION Task 8; commits `2df89a2`, `ab88443`): the "fixpoint" framing was wrong — Gilgamesch resolves the family structurally (B.3.2.15 cut immunity + fn6 all-stand rule); k1 is now a bounded three-pass regime, paradox tests in `tests/test_convoy_paradox.py`.
- **cmove dual source of truth** — CLOSED IN CODE (verified 2026-09-09): `conflict_game.parser:124-131` honors `ConvoyGraph.cmove_candidates` as single source of truth when a graph is supplied; the raw con-order scan survives only as documented legacy fallback for graph-less callers.
- **B.4.2.9 invalid-move + convoy interaction undefined** — CLOSED (MISSION Task 2; commit `0ce3042`): `geography/service.py` overrides geo-invalid mve to a valid cmove when the order index is in `cmove_candidates`; pinned by test (plus Task 12, commit `6969561`: B.4.2.9 umove reports `succeeds=False`).
- **Graph mode silently overrides `convoy_routing_engine`** — CLOSED (MISSION Task 11; commit `da154f3`): k1 logs a one-time warning when a `convoy_graph` is supplied AND `convoy_routing_engine` is explicitly set; the `fixed:` engine stays available for tests.
- **Lost `$cnv` debug event** — CLOSED (MISSION Task 11; commit `da154f3`): the graph path emits `$cnv:{path}` too; see switch tests.
- **`rule_interpretation_IX_3` / `IX_7`** — MAPPED (MISSION Task 13; commit `7cf22c3`): IX_3 ↔ DATC v3.2 6.D.10–6.D.14 + 6.D.20, IX_7 ↔ 6.E.4–6.E.6/6.E.12; switch-position tests landed. Residuals re-filed below (IX_3 value-0 drift, IX_7 validation).
- **Weak `test_6_a_1`** — CLOSED (MISSION Task 12; commit `6969561`): rewritten via `round_full`; geography rejects the illegal non-adjacent move.
- **DipNet evaluator not geography-aware** — CLOSED (MISSION Tasks 3–7; commits `0fd2f5d` → `c3b3d62`): `Order.via_convoy` wired end-to-end, GEO-009 adjacency, B.3.2.13 swap, writer con-reporting R1/R2 fixed. Gates: 100 games 1599 PASS / 3 FAIL, 1000 games 16790 PASS / 86 FAIL (was 16739/137) — every remaining FAIL triaged, zero engine bugs (see `project/doc/DIPNET_CONVOY_TRIAGE.md` final section). Residual FAIL families re-filed below (con-dest wire format, failed-convoy support reporting, documented Gilgamesch-vs-DipNet divergences).

Backlog filed 2026-09-09 from the MISSION reviews and Task 14 validation (do not fix silently; each needs its own task):

- **IX_3 value 0 converges toward value-2 behaviour in k4** — Gilgamesch's worked example for value 0 does not hold against the implementation; characterized (not endorsed) in `tests/test_rule_interpretations.py`. `exit:` Gilgamesch IX.3 re-analysis; if the premise is refuted, adjust the k4 chain handling accordingly.
- **IX_7 lacks `ge=0/le=2` validation** — `model.py:148` (`rule_interpretation_IX_7` has no bounds field validation; IX_3 has it). `exit:` add the validation in its own small task (behaviour change, not a docs fix).
- **stpsyr coast/board FAIL family** — 15 pre-existing FAILs in `tests_from_stpsyr/stpsyr_test_runner.py` (split-coast board-position comparison in the runner; e.g. `Rom`/`Ven` occupancy not compared on resolved coasts), plus test 32 whose expectation the corpus itself marks as non-DATC. `exit:` enrich the runner's board builder with `resolved_coast` information.
- **Legacy graph-less path counts GEO-004-invalid supports** — `conflict_game` without a `ConvoyGraph` is geography-blind by design and counts supports a geography phase would strike; same family as the old `test_6_a_1` TODO. `exit:` never fix inside the engine path; document as a legacy limitation in `project/doc/PHASES.md`.
- **`doc/_design/status.md` is a gitignored mirror with stale switch references** — ephemeral docs-prep output that still mentions the deleted `pattfields_include_failed_dests` switch. `exit:` regenerate via `make docs-prep` or ignore.
- **DipNet wire-format residuals (class c)** — the `con` mapping drops the convoy DESTINATION (DipNet `C A X - Y` vs our `con` keyed on the army's start), so a fleet offering a different destination than the army's stated move is invisible (`cSaeUT4h` family, 32 of the 86 remaining 1000-game FAILs); and DipNet marks a support of a failed convoyed move `no convoy` where the engine leaves `succeeds` unset (`D619QzLd` family, 29 of 86). `exit:` extend the pipeline mapping (con destination in the wire format / failed-chain support reporting decision). Full triage: `project/doc/DIPNET_CONVOY_TRIAGE.md` (2026-09-09 final section).
- **Documented Gilgamesch-vs-DipNet divergences (class b, no action unless DipNet parity becomes a goal)** — VIA-flagged move with no con order stands per B.3.2.14 where DipNet moves by land (17 of 86); unflagged adjacent move + con order ignores the convoy per B.3.2.14 sentence 3, con reports not-executed (2 of 86); bounced convoyed attack cuts support at its destination per standard rules where DipNet does not cut (1 of 86). `exit:` none (Gilgamesch semantics are authoritative per the MISSION spec hierarchy); revisit only for DipNet-parity work.

## Implementation Notes (stable)

- Conflict resolver remains field-name agnostic and should receive normalized superfields.
- Convoy routing works on superfields: armies start/end on superfields; sea fields have no subfields.
- Split-coast subfields are handled during early geography correction and retreat ordering, not inside the conflict algorithm.
- `standard.json` uses field-local `borders`; `MapDefinition`/`StandardMap` derive internal tuple-key `Edge`s for algorithmic use.
- `$convoy` is an explicit border marker and is independent of unit type `F`, so future variants can allow other convoying unit types.
- `tests/test_standard_map_fields_source.py` intentionally skips unless local `project/tests/standard.fields.txt` exists.
- **Strict rule:** `./pas/` is private/confidential, gitignored, never referenced in docs/commits/fixtures (enforcement: see Suggested Next Tasks #7).

---

## Appendix: Adversarial Plan Review Log

Plan reviewed: the roadmap/handoff sections now in this file (originally in `CLAUDE.md`).
Review run: 2026-06-23. Method: 6 parallel fresh-context `reviewer` subagents (Correctness&Logic,
Completeness, Edge Cases/Failure/Risks, Feasibility/Sequencing, Security/Safety/Data-loss,
Domain: Diplomacy rules & DATC). 3 rounds total.

### Round 1 — findings

Aggregated + deduped. CRITICAL = plan will fail/mislead; HIGH = real gap before proceeding.

**CRITICAL:**

- C1 Stale handoff: CLAUDE.md claimed ConvoyGraph integration "uncommitted" + "ahead 2"; reality = committed `62aa5e2` AND pushed (0 ahead of origin), with 6 more commits on top. Suggested Task #1 was a no-op. Verified by parent.
- C2 "DATC 10/10" overstates coverage: only 10 hand-picked cases of ~100 DATC v3.x. Misleading as compliance evidence.
- C3 6.D.3/6.F.1 "resolved" is masked, not fixed; bug mislocated to k2/k3. Real location: `writer` pattfields formula. Verified via `DATC_ANALYSIS.md`.
- C4 Convoy paradoxes unhandled/untested; k1 one-shot, not fixpoint.

**HIGH:** H1 Priority#1 contradicted "Geography Implemented"; H2 Priority#2 contradicted "DATC 10/10" + mislocated bug; H3 commit-before-validate sequencing; H4 stale verification numbers; H5 FastAPI/httpx blocker unscoped; H6 retreat+winter single bullets; H7 pattfields switch debt no exit; H8 DipNet 96.4% excludes inconclusive + evaluator not geography-aware; H9 graph mode silently bypasses convoy_routing_engine; H10 cmove dual source of truth; H11 B.4.2.9+convoy undefined; H12 weak test_6_a_1; H13 IX_3/IX_7 no DATC mapping; H14 `.pi/` untracked+ungitignored; H15 `./pas/` no enforcement gate; H16 dual lockfiles.

**Discarded (invalid):** "plan.md/progress.md ENOENT" — reviewer hallucinated a read instruction; plan was CLAUDE.md inline.

### Round 1 — revision applied

Rewrote into Roadmap / DATC Compliance (honest) / Current Handoff / Suggested Next Tasks / Known Gaps / Implementation Notes. Resolved C1–C4, H1–H16 in plan text; surfaced C4/H9/H10/H11/H12/H13/H8 as residual code gaps in Known Gaps.

### Round 2 — focused re-review (Correctness, Completeness, Domain)

Prior critical/high largely RESOLVED, but new issues:

- **CRITICAL (new, Domain):** DATC section numbering swapped in honest-status section (6.E vs 6.F). Two numbering schemes exist; `DATC_ANALYSIS.md` confirms dual scheme.
- **HIGH (new):** Project Overview still claimed "DATC 10/10 + DipNet 96.4%" unqualified; Task #2 self-defeating; Winter #4 no DoD; Known Gaps no exit criteria; inconsistent paradox range.
- MEDIUM/LOW: duplicate DATC heading; Task #9 placeholder; working-tree noise stale; self_cut_ok citation.

Revision: stated both numbering schemes; qualified Project Overview; unified paradox range to ≈6.F.13–6.F.23; reframed Task #2 as verify-or-dismiss; added Winter DoD; added per-gap `exit:`/`DECISION:`; relabeled self_cut_ok citation.

### Round 3 — final re-review (Correctness, Domain)

**Zero CRITICAL and zero HIGH** new plan-text findings. Remaining MEDIUM/LOW only. Stop rule met → **CLEAN ✅**.

Post-Round-3 cheap fixes (applied, not re-verified — cap reached): renamed original DATC section to "(history)" + softened "resolved"→"masked"; reframed Task #2 to verify-or-dismiss; removed Task #9 placeholder; fixed Roadmap #4 winter-test citation; softened working-tree noise to "non-exhaustive".

### Final Status: CLEAN ✅

Plan-text critical/high issues resolved across 3 rounds. Residual CODE gaps (not plan-fixable) are in `## Known Gaps` above with exit criteria.

Caveat: Round 3 Domain lens returned empty (no independent domain confirmation of the numbering fix); the Correctness lens found no residual domain inaccuracy. Re-run the Domain lens if a second domain-confirmation pass is wanted.
