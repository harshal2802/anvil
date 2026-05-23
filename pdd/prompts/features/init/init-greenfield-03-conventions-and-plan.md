# Phase 3: ConventionsScribe ∥ PlanScribe — parallel Flash calls

**Plan:** [PLAN-init-greenfield.md](PLAN-init-greenfield.md)
**Phase:** 3 of 4
**Estimated time:** ~45 min
**Dependencies:** Phase 2
**Flash calls:** 2 (parallel via `asyncio.gather`)

## Intent

Add the two remaining sub-agents. Both consume `project_md` and run in parallel after ProjectScribe. Outputs land on disk, then a single git commit captures the entire scaffold.

## What to build

### 1. Runtime sub-agent prompts (already drafted in this batch)
- [pdd/prompts/features/sub-agents/conventions_scribe.v1.0.0.md](../sub-agents/conventions_scribe.v1.0.0.md) + mirror
- [pdd/prompts/features/sub-agents/plan_scribe.v1.0.0.md](../sub-agents/plan_scribe.v1.0.0.md) + mirror

### 2. [anvil/orchestrator/schemas.py](../../../../anvil/orchestrator/schemas.py)
Add:

```python
class ConventionsScribeOutput(BaseModel):
    conventions_md: str
    decisions_md:   str

class PlanScribeOutput(BaseModel):
    plan_md:             str
    phase_01_prompt_md:  str
    plan_filename:       str = Field(description="PLAN-<area>.md")
    phase_01_filename:   str = Field(description="<area>-01-<phase-name>.md")
    feature_area:        str = Field(description="kebab-case subdirectory under pdd/prompts/features/")
```

### 3. [anvil/orchestrator/sub_agents.py](../../../../anvil/orchestrator/sub_agents.py)
Add `run_conventions_scribe(project_md, today)` and `run_plan_scribe(project_md, description, today)` following the ProjectScribe pattern.

### 4. [anvil/commands/init.py](../../../../anvil/commands/init.py)
Extend `_init_greenfield` after the ProjectScribe step:

```python
with console.status("[bold cyan]ConventionsScribe ∥ PlanScribe[/bold cyan] tailoring conventions and decomposing into phases…"):
    conv, plan = await asyncio.gather(
        run_conventions_scribe(project.project_md, today),
        run_plan_scribe(project.project_md, description, today),
    )

ctx = target / "pdd" / "context"
ctx.joinpath("conventions.md").write_text(conv.conventions_md, encoding="utf-8")
ctx.joinpath("decisions.md").write_text(conv.decisions_md, encoding="utf-8")

feature_dir = target / "pdd" / "prompts" / "features" / plan.feature_area
feature_dir.mkdir(parents=True, exist_ok=True)
(feature_dir / plan.plan_filename).write_text(plan.plan_md, encoding="utf-8")
(feature_dir / plan.phase_01_filename).write_text(plan.phase_01_prompt_md, encoding="utf-8")

_git_commit_initial(target, description)
```

Add `_git_commit_initial(target, description)`:
- `git add .`
- `git -c user.email=anvil@local -c user.name=anvil commit -m "chore: anvil init — <description first 60 chars>"`

## Acceptance

After `anvil init "Build a calculator agent that adds two numbers"`:
- `pdd/context/{project,conventions,decisions}.md` all present and stack-tailored.
- `pdd/prompts/features/<area>/PLAN-*.md` exists with 3-5 phases.
- `pdd/prompts/features/<area>/<area>-01-*.md` exists.
- `git log --oneline` shows exactly one commit.
- Wall time ≈ 15-20s (ProjectScribe ~7s + parallel pair ~10s).

## Risks

- `asyncio.gather` propagates the first exception; that's the right behavior — fail fast.
- `git commit` may fail if no `user.email` is globally configured — inline `-c user.email=...` flags handle that for the demo.

## Fallback (if time runs out)

Ship PlanScribe only; copy Anvil's own conventions/decisions verbatim into the new project. Note: this contradicts the user's "Flash-tailored" choice, so use only if Phase 3 blows past 60 min.
