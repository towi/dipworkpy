# AGENTS.md — dipworkpy living plan & handoff

> **Scope of this file:** the living roadmap, DATC-compliance status, current handoff state,
> next tasks, known gaps, and the adversarial plan review log. The stable project reference
> (overview, pipeline, notation, commands, data structures) lives in `CLAUDE.md`.
>
> Re-verify git state before acting on the handoff; the architectural corrections below are stable.

## Roadmap (Future Priorities)

> Verified 2026-06-23 against current `git log` and `project/doc/DATC_ANALYSIS.md`.

1. **Convoy paradox handling (DATC v3.2 convoy-paradox family, ≈6.F.13–6.F.23).** k1 currently does a **one-shot** post-dislodgement restriction of the `ConvoyGraph` to surviving convoyers. Pandin/Szykman-style paradoxes require a **fixpoint** (disrupted convoy → uncut support → un-dislodged fleet → restored convoy). No paradox test exists. This is the real frontier of the convoy work, not "border validation".
2. **Fix the pattfields formula in `conflict_game.writer` (NOT k2/k3).** `project/doc/DATC_ANALYSIS.md` states explicitly: the conflict resolution itself is correct; only the post-processing `pattfields = (efields | ufields) - sfields - (hfields - efields)` disagrees with DATC 6.D.3 / 6.F.1. These two cases pass today ONLY because `Switches.pattfields_include_failed_dests` (default **OFF**) gates them, and `test_conflict_game_02` depends on that default staying OFF. Convergence target: one rule that satisfies 6.D.3, 6.F.1, AND `test_conflict_game_02` simultaneously, then flip the default and delete the switch.
3. **Retreat conflict resolution.** Only `retreat_options` enumeration exists (`geography/retreat.py`). Two retreating units choosing the same field (DATC 6.H.10–6.H.16) is its own mini conflict engine and is not yet scoped. DoD: spec of retreat-conflict inputs/outputs + DATC 6.H.* tests + interaction with `pattfields`.
4. **Winter adjustments: support-center counting + build/disband.** Requires SC ownership tracking, year/season state, build/disband orders, civil-disorder rules. DoD: (a) data model for SC ownership + season/year on `Situation`/result; (b) phase integration point after Retreats in the round orchestrator; (c) DATC build/disband/civil-disorder tests. Currently no data model, no phase integration, no tests — scope as a milestone, not a one-liner.
5. **DipNet triage + geography-aware evaluation.** "96.4%" is measured on ~1600 cases from 100 games with the ~3.4% inconclusive convoy cases excluded, AND the DipNet evaluator does **not** feed `ConvoyGraph`/`order_geo_info` into the conflict resolver yet. Triage the 3.6% gap (bug vs mapping vs acceptable), then re-run with geography integration before citing a correctness figure.

## DATC Compliance (honest status)

"DATC 10/10" means **10 hand-picked cases** in `tests/test_conflict_datc.py`, not DATC v3.x compliance. The suite uses **DipworkPy-internal numbering** (see `tests/TEST_CASES_DATC.md`): 6.A basic, 6.B coast, 6.C circular, 6.D support, 6.E basic convoy, 6.F beleaguered, 6.G convoy paths, 6.H supports/dislodges, 6.I complex. **This differs from DATC v3.2 canonical**, where 6.E = Head-to-Head/Beleaguered and 6.F = Convoys (confirmed in `project/doc/DATC_ANALYSIS.md`).

Coverage gaps (internal numbering unless noted):

- **Convoy paradoxes** — DATC v3.2 convoy-paradox family (Pandin's, Szykman's, circular-disruption; ≈6.F.13–6.F.23) has **no** internal section and **no** test. This is the single biggest correctness gap; see Roadmap #1.
- **Beleaguered garrison** — only internal 6.F.1 / 6.F.2 covered; further DATC v3.2 6.E variants absent.
- **Support cut by dislodged unit** — only internal 6.H.1 covered.
- **Retreats** — no retreat section at all (full retreat conflict resolution unimplemented; see Roadmap #3).
- `test_6_a_1` is a weak assertion (TODO: should reject an illegal non-adjacent move once geography enforces it — but geography is marked Implemented, so this tension must be resolved: either GEO already classifies it via `OrderGeoInfo`/`umove`, or the TODO is stale).
- `rule_interpretation_IX_3` / `rule_interpretation_IX_7` have no DATC case mapping and are not tested across switch positions.

## DATC Compliance (history)

All 10 hand-picked DATC cases pass (see honest scope above). Historical 6.D.2 / 6.D.3 / 6.F.1 status:

- **6.D.2** — was already passing at the start of the re-architecture session
- **6.D.3** / **6.F.1** — **masked, not structurally fixed**: gated behind `Switches.pattfields_include_failed_dests` (default off), so the structurally-conflicting expectation in `test_conflict_game_02` also still passes

See `project/doc/DATC_ANALYSIS.md` for the per-case write-up.

## Current Handoff State (verified 2026-06-23)

Branch: `feat/service-architecture-and-ddl`, **pushed** (0 commits ahead of `origin`). HEAD: `2bb3f47`.

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

Fresh verification (2026-06-23): `make verify` → pass. (The earlier "66 passed / 99 passed, 1 skipped" figures were from 2026-05-19 and are stale; re-run the full subset before any correctness claim.)

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

- **Convoy paradox fixpoint** — k1 one-shot restriction is not provably convergent for DATC v3.2 convoy-paradox family (≈6.F.13–6.F.23). `exit:` Roadmap #1 lands a fixpoint + paradox tests.
- **cmove dual source of truth** — `ConvoyGraph.cmove_candidates` (from `geography/convoy.py`) is passed in but `conflict_game.parser` re-derives cmove status from raw `con` orders; the conflict engine silently ignores `cmove_candidates`. The two can disagree when geography invalidates a convoyer or flips `mve → umove` (B.4.2.9 `holds_no_support`). `DECISION:` honor the field or drop it from the wire format.
- **B.4.2.9 invalid-move + convoy interaction undefined** — a geo-invalid `mve` (→ `umove`) with matching `con` orders will not become a cmove, yet may still be listed in `cmove_candidates`; no test pins the chosen semantics. `exit:` add a test asserting the chosen semantics.
- **Graph mode silently overrides `convoy_routing_engine`** — `eval_k1.convoy_route_valid` short-circuits when `world.convoy_graph is not None`, ignoring `Switches.convoy_routing_engine="fixed:..."`. No warning when both are configured; no migration/deprecation plan for the `fixed:` engine. `DECISION:` warn, error, or document the override.
- **Lost `$cnv` debug event** — legacy `_convoy_route_valid_fixed` records the chosen route via `field.add_event("$cnv:{path}")`; the graph path adds no event. `exit:` graph path emits a `$cnv` event.
- **`rule_interpretation_IX_3` / `IX_7`** — values `0,1,2` have no documented DATC mapping; `self_cut_ok` default undocumented vs internal 6.D.4/6.D.5 (DATC v3.2 6.D.10/6.D.11). `exit:` add DATC case mapping + tests across switch positions.
- **Weak `test_6_a_1`** — assert-only TODO; illegal non-adjacent move not actually rejected. `exit:` tighten the assertion once GEO classification is confirmed.
- **DipNet evaluator not geography-aware** — see Roadmap #5. `exit:` evaluator feeds `ConvoyGraph`/`order_geo_info` and re-runs.

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
