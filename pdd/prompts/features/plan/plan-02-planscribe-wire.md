# Phase 2: Wire PlanScribe + write artifacts (1 Flash call)

**Plan:** [PLAN-plan.md](PLAN-plan.md)
**Phase:** 2 of 3
**Estimated time:** ~25 min
**Dependencies:** Phase 1 (project-root loader + `gh` pre-check + `project_md` in memory)
**Flash calls:** 1 (PlanScribe, reused verbatim)

## Intent

Now that Phase 1 has the current project's `pdd/context/project.md` loaded and `gh` confirmed, call the existing [run_plan_scribe](../../../../anvil/orchestrator/sub_agents.py) sub-agent to decompose the user's feature description into a `PLAN-<area>.md` + a phase-01 prompt, and write both artifacts to disk under `pdd/prompts/features/<area>/`. PlanScribe is reused **as-is** — no new sub-agent, no new schema, no new prompt file under `pdd/prompts/features/sub-agents/`. Phase 3 will layer `gh issue create` on top of the `PLAN-<area>.md` that this phase produces.

## What to build

### 1. Extend [anvil/commands/plan.py](../../../../anvil/commands/plan.py)

Phase 1 already shipped `PlanError`, `_find_project_root`, `_check_gh_available`, and the `execute()` skeleton. This phase **extends** `execute()` — does not rewrite it. The Phase 1 placeholder line `_ = project_md` and the "Phase 2 coming next" dim line are replaced by the new Flash wiring.

Add imports at the top:

```python
import asyncio
from datetime import date

from anvil.orchestrator.gemini import GeminiAuthError, GeminiResponseError
from anvil.orchestrator.schemas import PlanScribeOutput
from anvil.orchestrator.sub_agents import run_plan_scribe
```

### 2. New async helper `_plan_feature(...)`

```python
async def _plan_feature(
    feature: str,
    project_root: Path,
    project_md: str,
    today: str,
) -> None: ...
```

Body:

1. `with console.status("[bold cyan]PlanScribe[/bold cyan] decomposing into phases…"):` wrap a single `await run_plan_scribe(project_md=project_md, description=feature, today=today)` call. Capture the `PlanScribeOutput` as `output`.
2. Compute `feature_dir = project_root / "pdd" / "prompts" / "features" / output.feature_area`.
3. **Collision check:** if `feature_dir` exists AND `next(feature_dir.glob("PLAN-*.md"), None)` is not `None`, raise `PlanError(f"Feature area '{output.feature_area}' already has a PLAN. Use a different feature description or remove {feature_dir} and retry.")`. This mirrors the slug-collision UX in [anvil/commands/init.py](../../../../anvil/commands/init.py). `--force` is out of scope for the demo per PLAN-plan.md.
4. `feature_dir.mkdir(parents=True, exist_ok=True)`, then:
   - `(feature_dir / output.plan_filename).write_text(output.plan_md, encoding="utf-8")`
   - `(feature_dir / output.phase_01_filename).write_text(output.phase_01_prompt_md, encoding="utf-8")`
5. Print the green confirmation matching `init.py`'s tone:

```
[green]✓[/green] PlanScribe → [dim]{output.feature_area}/{output.plan_filename}[/dim] + phase-01 prompt
```

### 3. Rewire `execute()`

After the existing `try` block that resolves `project_root`, calls `_check_gh_available()`, and reads `project_md`, replace the Phase 1 placeholder block:

```python
_ = project_md
console.print(
    f"[bold cyan]anvil plan[/bold cyan] — feature: [italic]{feature}[/italic]\n"
    f"[dim]project root: {project_root}[/dim]"
)
console.print("[dim]Phase 2 wires PlanScribe — coming next.[/dim]")
```

with:

```python
console.print(
    f"[bold cyan]anvil plan[/bold cyan] — feature: [italic]{feature}[/italic]\n"
    f"[dim]project root: {project_root}[/dim]"
)
today = date.today().isoformat()
try:
    asyncio.run(_plan_feature(feature, project_root, project_md, today))
except PlanError as e:
    console.print(f"[red]{e}[/red]")
    raise SystemExit(1) from e
except GeminiAuthError as e:
    console.print(f"[red]{e}[/red]")
    raise SystemExit(2) from e
except GeminiResponseError as e:
    console.print(f"[red]Flash returned malformed output:[/red] {e}")
    raise SystemExit(2) from e

console.print(
    "\n[bold green]Done.[/bold green] Opened the PLAN. "
    "Next: [bold]anvil plan[/bold] phase 3 (gh issues) or hand-edit the PLAN."
)
```

Exit-code split mirrors [init.py](../../../../anvil/commands/init.py):

- `PlanError` (filesystem / collision) → exit 1
- `GeminiAuthError` / `GeminiResponseError` → exit 2

## Acceptance

- `anvil plan "Add a refund-eligibility node…"` from inside Anvil's own project shows the Phase 1 banner, then the PlanScribe spinner, then a green checkmark line, then the "Done." footer. Exits 0.
- Two new files exist under `pdd/prompts/features/<area>/`: `PLAN-<area>.md` and `<area>-01-<phase>.md`. Both are non-empty UTF-8.
- Re-running the same command (same feature_area) fails with a red `PlanError` mentioning the existing feature_dir, exits 1. No Flash call is repeated — wait, it *is* re-paid (PlanScribe runs before the collision check, since we only know the slug after the call). That's acceptable per the PLAN: same trade-off as init.py's post-Flash slug-collision.
- With `GOOGLE_API_KEY` unset, the command fails with a red Rich message and exits 2 (GeminiAuthError surfaces from inside `_plan_feature`).
- `from __future__ import annotations` retained; full type hints; mypy --strict clean; no bare `except:`; no `print()`; no multi-paragraph docstrings.

## Risks

- **Post-Flash collision discovery.** As noted above, PlanScribe runs before we know `output.feature_area`, so a collision wastes one Flash call. Mitigation: deferred to a follow-up `--force` flag. Documented in PLAN-plan.md "Out of scope".
- **`feature_dir.glob("PLAN-*.md")` glob mismatch.** PlanScribe is contracted to produce filenames of the form `PLAN-<area>.md` (see [PlanScribeOutput](../../../../anvil/orchestrator/schemas.py)), so the glob will match its own output. If the schema description ever drifts to `Plan-<area>.md` or `plan_<area>.md`, this check silently misses. Mitigation: relies on the schema's `Field(description=...)` staying truthful; covered by the structural test that Phase 3 adds.
- **`asyncio.run` inside a sync `execute()`.** Mirrors `init.py` exactly — acceptable. Do not refactor `execute()` to async; the Typer entry point is sync.
