---
name: PLAN-init-greenfield
description: Implementation plan for `anvil init "<sentence>"` — greenfield project scaffolding
---

# Implementation Plan: anvil init (greenfield)

**Created:** 2026-05-23
**Complexity:** Medium-High (3 new Flash sub-agents + new command + filesystem scaffolding + one eval)
**Estimated phases:** 4
**Time budget:** ~115 min (~2 hours to demo, ~5 min buffer — tight)

## Summary

`anvil init "<sentence>" [--out DIR]` turns one English description into a real LangGraph project directory: a scaffolded repo with a tailored `pdd/` tree, git history, and the artifacts that `anvil run --phase 1` (already shipped, see [commands/run.py](../../../../anvil/commands/run.py)) consumes — `pdd/context/{project,conventions,decisions}.md`, a `PLAN-*.md`, and one phase-01 prompt. Generation runs as a 3-step Flash flow with parallelism in step 2, mirroring the existing per-phase orchestrator shape in [decisions.md](../../../context/decisions.md) ("Three-step sub-agent execution shape").

## Demo path

```bash
anvil init "Build a customer support agent: triage email, draft reply, escalate low-confidence to humans"
# → creates ./customer-support-agent/ with tailored pdd/, git init, first commit
cd customer-support-agent
anvil run --phase 1   # already wired; sub-agents produce code + evals + ADR + PR
```

## Runtime shape (3 Flash calls, 2 wall-time steps)

```
ProjectScribe                                  step 1 (sequential — gives slug + context)
      │
      ├── ConventionsScribe                    step 2 (parallel via asyncio.gather)
      └── PlanScribe                           step 2
```

Mirrors the existing per-phase shape `NodeForge → (EvalSmith ∥ DocScribe) → MergeBot` but stops at step 2 (no MergeBot-equivalent — `init` doesn't open a PR for itself).

## Phases

### Phase 1: Scaffold + `--out` + git (no Flash)

**Produces:**
- [anvil/commands/init.py](../../../../anvil/commands/init.py) rewritten — takes `description`, `existing`, `out` args; validates `out` (default cwd, error if collision after slug resolves); the function is *prepared* but the directory creation itself happens after ProjectScribe returns the slug.
- A helper `anvil/commands/_init_scaffold.py` (or inline) that, given a slug and a target parent dir, creates `<parent>/<slug>/pdd/{context,prompts/features,evals/{baselines,scripts}}`, an empty `src/`, and runs `git init` + first commit.
- Argument plumbing through [anvil/cli.py](../../../../anvil/cli.py): add `--out` to `init_cmd`.

**Depends on:** nothing
**Risk:** Low — pure I/O + `subprocess` git. Watch: collision detection happens AFTER Flash call 1 returns the slug, so error UX must be clean (Flash already paid for).
**Prompt:** `pdd/prompts/features/init/init-greenfield-01-scaffold.md`

### Phase 2: ProjectScribe — Flash call 1

**Produces:**
- New sub-agent prompt `pdd/prompts/features/sub-agents/project_scribe.v1.0.0.md` (mirrored to `anvil/prompts/sub-agents/` per the convention in [conventions.md](../../../context/conventions.md))
- New Pydantic schema in [anvil/orchestrator/schemas.py](../../../../anvil/orchestrator/schemas.py): `ProjectScribeOutput { project_slug: str, project_md: str }`
- New function in [anvil/orchestrator/sub_agents.py](../../../../anvil/orchestrator/sub_agents.py): `run_project_scribe(description: str) -> ProjectScribeOutput`, temperature 0.4 (prose)
- Wire into `anvil/commands/init.py`: call ProjectScribe first → resolve target dir from slug → scaffold → write `pdd/context/project.md`

**Depends on:** Phase 1
**Risk:** Medium — first new Flash sub-agent in this feature; sets the pattern. Mitigation: reuse the existing structured-output plumbing from [orchestrator/sub_agents.py](../../../../anvil/orchestrator/sub_agents.py) verbatim.
**Prompt:** `pdd/prompts/features/init/init-greenfield-02-project-scribe.md`

### Phase 3: ConventionsScribe ∥ PlanScribe — Flash calls 2 & 3 in parallel

**Produces (one phase, two sub-agents — they share the same code shape so one prompt is enough):**
- Two sub-agent prompts: `conventions_scribe.v1.0.0.md` (tailors `conventions.md` + `decisions.md` to the inferred stack) and `plan_scribe.v1.0.0.md` (decomposes into phases, writes `PLAN-<feature>.md` + the `phase-01` prompt body for the agent's first feature). Both mirrored to `anvil/prompts/sub-agents/`.
- Two schemas in `schemas.py`: `ConventionsScribeOutput { conventions_md, decisions_md }`, `PlanScribeOutput { plan_md, phase_01_prompt_md, plan_filename, phase_01_filename, feature_area }`
- Two functions in `sub_agents.py`: `run_conventions_scribe`, `run_plan_scribe` — both temp 0.4, both take `project_md` as input
- Wire into `init.py`: `await asyncio.gather(run_conventions_scribe(...), run_plan_scribe(...))`, write all four output files into the right places, then make the initial git commit.

**Depends on:** Phase 2 (needs `project.md` text as context input)
**Risk:** Medium-High — biggest phase by surface area. Mitigation: ConventionsScribe is the simplest call (two markdown strings out); PlanScribe is the one most likely to need iteration. If we slip, ship ConventionsScribe first and pin PlanScribe to a template fallback for the demo.
**Prompt:** `pdd/prompts/features/init/init-greenfield-03-conventions-and-plan.md`

### Phase 4: Structural eval

**Produces:** `tests/test_init_greenfield.py` with one `@pytest.mark.live` test that:
1. Runs `anvil init "Build a calculator agent that adds two numbers" --out tmp_path` (calls the Typer app via `CliRunner` or `subprocess`)
2. Asserts file tree: `<slug>/pdd/context/{project,conventions,decisions}.md`, `<slug>/pdd/prompts/features/<area>/PLAN-*.md`, one `*-01-*.md` phase prompt, `<slug>/.git/`
3. Asserts `project.md` contains "calculator" (substring — proves Flash got the description)
4. Asserts `git log` shows ≥1 commit
5. NOT an LLM-as-judge eval — golden datasets don't fit in 2 hours; this is a structural smoke test.

**Depends on:** Phase 3
**Risk:** Low — but hits real Flash. The `@pytest.mark.live` marker keeps CI safe; demo runs it manually.
**Prompt:** `pdd/prompts/features/init/init-greenfield-04-eval.md`

## Risks & Unknowns

- **Time budget is tight (~5 min buffer).** If Phase 3 slips past the 45-min mark, fall back: ship PlanScribe only, copy Anvil's conventions/decisions verbatim for the demo, and post-hackathon promote ConventionsScribe.
- **Flash latency for ProjectScribe blocks scaffold.** ~5-10s. Show a Rich spinner; users tolerate it because nothing has been written to disk yet.
- **Slug collisions:** ProjectScribe might emit a slug that already exists in `--out`. Resolution: error with a clear message ("`./customer-support-agent` already exists — pass `--out` to write elsewhere"). No silent overwrite.
- **`anvil run --phase 1` consumption contract:** `run.py` already expects specific filenames/paths for phase prompts. PlanScribe must emit `phase_01_filename` exactly matching what `run.py` looks for. Verify this contract during Phase 3 implementation — see [commands/run.py](../../../../anvil/commands/run.py).

## Decisions resolved (logged here, not yet copied to decisions.md)

| Decision | Choice | Why |
|---|---|---|
| Slug source | Flash-derived (in `ProjectScribeOutput.project_slug`) | Demo polish; one less arg to teach |
| Directory location | cwd default, `--out` flag, error if target exists | Safe + flexible without a yes/no prompt |
| Conventions/decisions content | Flash-generated, tailored to inferred stack | Dogfooding + demo strength; cost is one extra Flash call (parallelized) |

→ Copy these into [pdd/context/decisions.md](../../../context/decisions.md) before Phase 2 lands (the slug + conventions decisions belong in the durable record).

## Out of scope (post-demo)

- `anvil init --existing` (brownfield)
- LLM-as-judge eval over `project.md` quality
- Multi-language scaffold templates (TS/Go)
- Interactive disambiguation for vague descriptions
- Pre-creating a GitHub repo via `gh repo create`
- Drift detection between Anvil's own `pdd/` and generated projects' `pdd/`
