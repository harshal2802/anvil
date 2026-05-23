# Phase 2: ProjectScribe — first Flash call

**Plan:** [PLAN-init-greenfield.md](PLAN-init-greenfield.md)
**Phase:** 2 of 4
**Estimated time:** ~30 min
**Dependencies:** Phase 1
**Flash calls:** 1 (sequential — gives slug + context for downstream calls)

## Intent

Add the first new sub-agent. Calls Flash with the user's description and returns `(project_slug, project_md)`. Wires into the init command so the directory is created using the Flash-derived slug, and the first context file (`pdd/context/project.md`) lands on disk.

## What to build

### 1. Runtime sub-agent prompts (already drafted in this batch)
- [pdd/prompts/features/sub-agents/project_scribe.v1.0.0.md](../sub-agents/project_scribe.v1.0.0.md) (canonical)
- [anvil/prompts/sub-agents/project_scribe.v1.0.0.md](../../../../anvil/prompts/sub-agents/project_scribe.v1.0.0.md) (mirror for `importlib.resources`)

### 2. [anvil/orchestrator/schemas.py](../../../../anvil/orchestrator/schemas.py)
Add:

```python
class ProjectScribeOutput(BaseModel):
    project_slug: str = Field(description="kebab-case, 2-5 words")
    project_md:   str = Field(description="full markdown body of pdd/context/project.md")
```

### 3. [anvil/orchestrator/sub_agents.py](../../../../anvil/orchestrator/sub_agents.py)
Add:

```python
async def run_project_scribe(description: str, today: str) -> ProjectScribeOutput:
    spec = load_sub_agent_prompt("project_scribe")
    user_message = spec.render(description=description, today=today)
    return await run_agent(
        system_instruction=spec.system_instruction,
        user_message=user_message,
        response_schema=ProjectScribeOutput,
        temperature=spec.temperature,
    )
```

### 4. [anvil/commands/init.py](../../../../anvil/commands/init.py)
Promote `_init_greenfield` from stub to:

```python
async def _init_greenfield(description: str, out: Path) -> None:
    today = date.today().isoformat()
    with console.status("[bold cyan]ProjectScribe[/bold cyan] is naming the project…"):
        project = await run_project_scribe(description, today)

    target = (out / project.project_slug).resolve()
    if target.exists():
        raise typer.BadParameter(f"{target} already exists — pass --out to write elsewhere.")
    _scaffold_project(target)
    (target / "pdd" / "context" / "project.md").write_text(project.project_md, encoding="utf-8")
    console.print(f"[green]✓[/green] Project: [bold]{target}[/bold]")
```

(Phase 3 extends this with the parallel step + the git commit.)

## Acceptance

- `anvil init "Build a customer support agent: triage email, draft reply, escalate low-confidence cases to humans"` creates a Flash-chosen directory under cwd (e.g., `./customer-support-agent/`) and writes a tailored `pdd/context/project.md`.
- Rich spinner is visible during the ~5-10s Flash call.
- `GeminiAuthError` surfaces with a clear Rich-formatted message when `GOOGLE_API_KEY` is unset.

## Risks

- Flash schema-violation → reused `GeminiResponseError`; print the truncated raw output and exit 2.
- Slug collision with an existing directory → clean error, no overwrite. The Flash call already spent is acknowledged in the error message.
