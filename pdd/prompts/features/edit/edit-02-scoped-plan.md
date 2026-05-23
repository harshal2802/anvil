# Phase 2: Scoped PlanScribe invocation

**Plan:** [PLAN-edit.md](PLAN-edit.md)
**Phase:** 2 of 4
**Estimated time:** ~25 min
**Dependencies:** Phase 1 (detection)
**Flash calls:** 1 (PlanScribe, reused verbatim)

## Intent

Take the `target_node` identified in Phase 1 and run PlanScribe with that node as the scoping anchor, producing exactly one phase's worth of artifacts. Reuse `run_plan_scribe` verbatim — wrap it in a thin adapter `run_plan_scribe_scoped` that prepends `"Single-node change to \`{target_node}\`:"` to the description. No new sub-agent prompt, no schema change.

## What to build

### 1. [anvil/orchestrator/sub_agents.py](../../../../anvil/orchestrator/sub_agents.py)
Add ONE new function next to `run_plan_scribe`:

```python
async def run_plan_scribe_scoped(
    project_md: str, change: str, target_node: str, today: str
) -> PlanScribeOutput:
    scoped_description = f"Single-node change to `{target_node}`: {change}"
    return await run_plan_scribe(
        project_md=project_md, description=scoped_description, today=today
    )
```

No other changes. Do not touch existing functions or imports.

### 2. [anvil/commands/edit.py](../../../../anvil/commands/edit.py)
Extend `execute()` with a new async helper `_scoped_plan(change, project_root, target_node)`:

- Read `<project_root>/pdd/context/project.md`.
- Call `await run_plan_scribe_scoped(...)` inside a `console.status("[bold cyan]PlanScribe[/bold cyan] scoping plan to {target_node}…")` Rich spinner.
- Assert exactly 1 phase in `output.plan_md` (regex `r"^### Phase \d+:"` multiline count). If not 1, raise `EditError("edit is single-node only — split the change and rerun. PlanScribe returned N phases.")`.
- Compute the next phase number in `pdd/prompts/features/<feature_area>/` by globbing existing `*-NN-*.md`, taking max + 1 (default 1).
- Rename `output.phase_01_filename` (templated as `<area>-01-<name>.md`) by replacing `01` with the computed `NN`. Write the phase prompt body.
- Compute the PLAN filename as `PLAN-edit-{_slugify(change)}.md` (`_slugify` lowercases, replaces non-alnum with `-`, trims, caps at 40 chars).
- Write both files. Print Rich green confirmation.

Catch `EditError → SystemExit(1)`, `GeminiAuthError|GeminiResponseError → SystemExit(2)`, shaped like `commands/init.py`.

Update the Phase 1 placeholder line ("Phase 2 wires scoped PlanScribe — coming next") → `[dim]Phase 3 wires forge_phase — coming next.[/dim]`.

## Acceptance

- `run_plan_scribe_scoped(...)` returns the same `PlanScribeOutput` shape as `run_plan_scribe` — no schema diff.
- A simulated PlanScribe returning 2+ phases triggers `EditError`; returning exactly 1 phase writes both files.
- The phase prompt is written with NN ≥ 1 (next number after existing phases under `feature_area/`).
- The PLAN filename slug stays under 40 chars and contains only `[a-z0-9-]`.
- `make lint` (ruff + mypy --strict) clean.

## Risks

- **PlanScribe was tuned for 3-5 phases.** Forcing 1 phase via the description template might produce a low-quality plan. Mitigation: ship as-is; bump to `plan_scribe.v1.1.0` with a `mode` template variable only if v1.0.0 produces visibly worse 1-phase plans (per PLAN-edit.md Decisions table).
- **PlanScribe heading format drift.** The single-phase regex assumes `### Phase N:` exactly. Same risk surfaces in [plan-03-gh-issues.md](../plan/plan-03-gh-issues.md) — if the format drifts, both break.
- **Slug collisions.** Two edits with similar phrasings may produce the same `PLAN-edit-<slug>.md`. Phase 2 silently overwrites; v1 accepts this. Add collision detection in a follow-up if it bites in practice.
