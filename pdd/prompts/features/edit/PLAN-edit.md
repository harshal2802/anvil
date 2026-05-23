---
name: PLAN-edit
description: Implementation plan for `anvil edit "<change>"` — conversational, single-node extension of an existing Anvil project
---

# Implementation Plan: anvil edit

**Created:** 2026-05-23
**Complexity:** Medium (composition over orchestration — reuses `run_plan_scribe` and `forge_phase` verbatim; one new detection step is the only net-new logic)
**Estimated phases:** 4
**Time budget:** ~95 min (~1.5 hours to demo, comfortable buffer because most of the machinery already exists)

## Summary

`anvil edit "<change>"` is the conversational surface on top of work that already ships: it detects which existing node(s) a plain-English change touches, runs `PlanScribe` with that node as the scoping anchor to produce a one-phase plan, then invokes the existing `forge_phase` orchestrator to ship the change as a PR. Per [decisions.md](../../../context/decisions.md) ("Conversational `anvil edit` is composition, not new orchestration"), this is `plan` + `run` chained with a single new step in front — no new sub-agents, no parallel orchestrator, no edit-specific Flash plumbing. v1 is single-target only; multi-node edits are out of scope.

## Demo path

```bash
cd customer-support-agent              # project produced by `anvil init`
anvil run --phase 1                    # baseline: one node shipped, on main
anvil edit "Also tag each reply with the detected language so downstream routing can use it"
# → detects: triage_email is the touched node
# → PlanScribe emits PLAN-edit-language-tag.md + a phase-01 prompt scoped to that change
# → forge_phase runs NodeForge → (EvalSmith ∥ DocScribe) → MergeBot
# → second PR opened, ADR explains why language detection lives in the triage node
```

## Runtime shape (1 detection step + 1 Flash plan call + the existing 3-step forge_phase)

```
detect_target_node           step 0   (deterministic OR 1 Flash call — open decision)
        │
        ▼
PlanScribe (scoped)          step 1   (1 Flash call — reuses run_plan_scribe)
        │
        ▼
forge_phase                  steps 2-4 (NodeForge → EvalSmith ∥ DocScribe → MergeBot — unchanged)
```

Net new wall time over `anvil run`: one Flash call (PlanScribe) plus the detection step. If detection is deterministic, the only added latency is PlanScribe (~5-10s).

## Phases

### Phase 1: Project-state loader + target-node detection

**Produces:**
- [anvil/commands/edit.py](../../../../anvil/commands/edit.py) rewritten: reads `pdd/context/project.md` from cwd to confirm this is an Anvil project (exits cleanly with a Rich error if not — same shape as the `--existing` branch in [anvil/commands/init.py](../../../../anvil/commands/init.py)), enumerates already-shipped nodes by listing `src/nodes/*.py` (or `pdd/prompts/features/<area>/*-NN-*.md` if the source-of-truth question lands on prompts).
- A helper `_detect_target_node(change: str, existing_nodes: list[NodeSummary]) -> str` that returns the single node name the change targets. v1 implementation choice — see Decisions table — is one of:
  - **Deterministic:** substring/keyword match of `change` against node names + their `reads_from_state`/`writes_to_state` lists, falling back to "ambiguous → ask user to disambiguate via stdout list" if score is tied.
  - **Flash:** a tiny structured-output call returning `{target_node: str, confidence: float, reasoning: str}`.
- If detection is ambiguous (deterministic) or low-confidence (Flash), print the candidate list and exit 1 with a "rerun with `anvil edit \"<change> in <node-name>\"`" hint. No interactive prompt — keep the surface non-blocking.

**Depends on:** nothing
**Risk:** Medium — the detection step is the only net-new design surface in this whole feature; the rest is reuse. Deterministic is faster to ship but UX is worse on phrasings that don't share vocabulary with node names. Flash is more forgiving but adds latency, cost, and a 7th-style "mini sub-agent" we have to maintain. Mitigation: ship deterministic first, leave a comment marking the Flash-call expansion point.
**Prompt:** `pdd/prompts/features/edit/edit-01-detect.md`

### Phase 2: Scoped PlanScribe invocation

**Produces:**
- A new function in [anvil/orchestrator/sub_agents.py](../../../../anvil/orchestrator/sub_agents.py): `run_plan_scribe_scoped(project_md: str, change: str, target_node: str, today: str) -> PlanScribeOutput`. Internally just calls the existing `run_plan_scribe` with a templated description (`f"Single-node change to `{target_node}`: {change}"`) — no schema change, no new sub-agent prompt.
- A small adapter in `anvil/commands/edit.py` that takes PlanScribe's output and writes only the phase-01 prompt into the project's existing `pdd/prompts/features/<area>/` (next NN suffix — count existing `*-NN-*.md` files and increment). The `PLAN-<area>.md` is written as `PLAN-edit-<change-slug>.md` next to it.
- Hard-code an assertion that PlanScribe returns exactly 1 phase for the edit path; if it returns more, error out with a clear message ("edit is single-node only — split the change and rerun"). This keeps the contract honest without a schema change.

**Depends on:** Phase 1 (needs `target_node` and `project_md`)
**Risk:** Low — verbatim reuse of [plan_scribe.v1.0.0.md](../sub-agents/plan_scribe.v1.0.0.md). Watch: PlanScribe was designed for greenfield 3-5 phases, but its system prompt is permissive enough that "produce one phase only" works via the description text. If it doesn't, the fallback is a `.v1.1.0` bump that adds a `mode: greenfield | edit` template variable — but try the cheap path first.
**Prompt:** `pdd/prompts/features/edit/edit-02-scoped-plan.md`

### Phase 3: Wire `forge_phase` against the new phase prompt

**Produces:**
- The remaining body of `anvil/commands/edit.py`: build a `PhaseInput` (from [anvil/orchestrator/sub_agents.py](../../../../anvil/orchestrator/sub_agents.py)) by reading the just-written phase-01 prompt body as `user_intent`, harvesting `existing_nodes_json` from the same node enumeration used in Phase 1, loading `state_schema_source` from `src/state.py` (file-not-found errors here are user-facing — they mean the project wasn't scaffolded by `anvil init`), and the project's `conventions.md`-derived `repo_conventions_json`.
- Call `await forge_phase(phase_input)` — no changes to `sub_agents.py`'s execution shape. The same NodeForge → (EvalSmith ∥ DocScribe) → MergeBot sequence ships the change.
- Write artifacts back into the project (not `./test-output/`): node into `src/nodes/<filename>` (overwriting only after a diff-preview confirmation? — leave that decision for implementation; safer first cut is to write to `src/nodes/<filename>.new` and let the user `mv` after review).
- Reuse the artifact-writing helpers from [anvil/commands/run.py](../../../../anvil/commands/run.py) — extract them to `anvil/orchestrator/artifacts.py` only if `run.py` and `edit.py` would otherwise duplicate the logic.

**Depends on:** Phase 2 (needs the phase-01 prompt body and the target node identity)
**Risk:** Medium — this is where the "composition" claim earns or loses its keep. If `forge_phase`'s `PhaseInput` shape doesn't fit the edit case cleanly (e.g., `next_adr_number` needs project-aware bumping rather than the hardcoded `"001"` in [commands/run.py](../../../../anvil/commands/run.py)), we have to add ADR-number discovery here. That's a one-liner glob + max(), not a schema change, but flag it. Watch also: `existing_nodes_json` needs to include the target node itself (so NodeForge knows it's *replacing* logic, not adding a sibling) — `run.py`'s current callsite only lists *prior* nodes.
**Prompt:** `pdd/prompts/features/edit/edit-03-forge.md`

### Phase 4: Live eval — end-to-end smoke test

**Produces:** `tests/test_edit.py` with one `@pytest.mark.live` test that:
1. Uses a tmp project produced by `anvil init "Build a calculator agent that adds two numbers"` (or a fixture checked into `tests/fixtures/edit-baseline/` if init latency makes the test painful).
2. Runs `anvil run --phase 1` against the fixture so there's at least one node to edit.
3. Runs `anvil edit "Also return the operation as a string (e.g., '2 + 3') alongside the numeric result"` via Typer's `CliRunner` or `subprocess`.
4. Asserts: a second phase-NN prompt exists under the same `feature_area/`, a new ADR file lands in `docs/adr/`, the target node's module was rewritten (file mtime or content diff), and `git log` shows a new commit.
5. Structural-only — no LLM-as-judge. Same posture as the `init` eval in [PLAN-init-greenfield.md](../init/PLAN-init-greenfield.md): catches plumbing breakage, not quality regressions.

**Depends on:** Phase 3
**Risk:** Low — but hits real Flash twice (init bootstrap + edit). `@pytest.mark.live` keeps CI safe; demo runs it manually. If the init fixture is too slow, check the baseline project into `tests/fixtures/` and skip Phase 4's step 1+2.
**Prompt:** `pdd/prompts/features/edit/edit-04-eval.md`

## Risks & Unknowns

- **Detection accuracy is the entire UX.** A wrong target node sends the rest of the pipeline down a wrong path with full confidence — there's no downstream check that says "wait, this change really belonged in `draft_reply`, not `triage_email`." Mitigation: aggressive low-confidence-exit on the deterministic path, and surface the detected node in the spinner text so users see it before PlanScribe runs.
- **PlanScribe was tuned for 3-5 phases, not 1.** If forcing it to one phase produces low-quality plans, we either bump `plan_scribe.v1.1.0` with an edit-mode template or write a thin `edit_planner.v1.0.0` prompt — but only after measuring. Don't preempt this in v1.
- **`forge_phase`'s `next_adr_number` is hardcoded.** Edit projects have ≥1 ADR already; this needs a glob+max+1 helper. Trivial but easy to forget.
- **NodeForge replacing vs extending a node.** When the target node already exists, NodeForge needs to know it's producing a replacement, not a new sibling. The current sub-agent prompt doesn't have an explicit "you are editing, not creating" channel — for v1, encoding this in the phase-01 prompt's `## Intent` section is sufficient (PlanScribe already controls that text). Watch for hallucinated function name renames.
- **Overwrite policy.** Writing directly over `src/nodes/<name>.py` is destructive; writing to `<name>.py.new` is safer but adds a manual step. Phase 3 picks one — flag for review.

## Decisions resolved (logged here, copy to decisions.md when settled)

| Decision | Choice | Why |
|---|---|---|
| Detection mechanism (deterministic vs Flash) | **OPEN — pick during Phase 1 implementation** | Deterministic = no extra Flash cost, instant, but brittle on rephrasings ("language tagging" vs node name `triage_email`). Flash = forgiving, costs one extra ~5s call + maintenance of a 5th orchestrator surface. Default to deterministic for v1, leave a comment marking the Flash-expansion site. Revisit if demo phrasings miss. |
| Single-target only in v1 | Yes | Multi-node edits explode the contract: NodeForge runs once, MergeBot ships one PR. Multi-node = either multiple PRs (out of scope) or a bundled PR (violates PR-per-phase per [decisions.md](../../../context/decisions.md)). Defer. |
| Reuse `PlanScribe` vs new edit-mode sub-agent | Reuse | Composition-not-orchestration mandate from [decisions.md](../../../context/decisions.md). Bump to `v1.1.0` with a `mode` flag only if v1.0.0 produces visibly worse 1-phase plans. |
| Source-of-truth for existing-node enumeration (`src/nodes/*.py` vs `pdd/prompts/features/*/*-NN-*.md`) | `src/nodes/*.py` | The filesystem after `anvil run` is the ground truth; phase prompts can drift (e.g., aborted runs). |
| Overwrite policy for the target node module | **OPEN — pick during Phase 3 implementation** | `.new` suffix is safer; direct overwrite is the better demo. Probably ship `.new` + a Rich-printed `mv` command. |

→ Once Phase 1 lands and the detection mechanism is chosen, append a decisions.md entry: "anvil edit detection is deterministic / Flash-based" with the same justification.

## Out of scope (post-demo)

- Multi-node edits (split into multiple sequential `anvil edit` calls for now)
- Interactive disambiguation when detection is low-confidence (today: print candidates and exit 1)
- Edits that *delete* a node (only add/replace in v1)
- Edits that change the state schema in breaking ways (NodeForge can add new fields; removing fields is unsafe without a migration)
- A second LLM-as-judge eval comparing before/after node behavior on the golden dataset
- Undo / revert support beyond `git reset` (the per-edit commit is the unit of revert)
- Cross-project edits / monorepo support
