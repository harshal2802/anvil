# Phase 2: Rich rendering + command wiring (no Flash)

**Plan:** [PLAN-status.md](PLAN-status.md)
**Phase:** 2 of 3
**Estimated time:** ~15 min
**Dependencies:** Phase 1 (`anvil/commands/_status_scan.py`)
**Flash calls:** 0

## Intent

Turn the read-only scanner from Phase 1 into the user-visible `anvil status` command. Replace the 17-line stub in [anvil/commands/status.py](../../../../anvil/commands/status.py) with a real `execute() -> None` that calls `scan_project(Path.cwd())` and renders three Rich tables — Phases, Evals, Prompts — on a single `Console`. Color contract matches [anvil/commands/init.py](../../../../anvil/commands/init.py) and [anvil/commands/run.py](../../../../anvil/commands/run.py): green check for "done," yellow dot for "prompt-only," dim dash for "not started." Failure path is Rich-formatted with `SystemExit(1)`, never a traceback.

## What to build

### 1. [anvil/commands/status.py](../../../../anvil/commands/status.py) (REWRITE)

Module docstring: one line. `from __future__ import annotations` at top. Full type hints. No `print()` — `rich.console.Console` only.

#### Public surface

```python
def execute() -> None: ...
```

#### Behavior

1. **Pre-check.** If `Path.cwd() / "pdd"` does not exist or is not a directory, print one Rich line and exit:

   ```
   Not inside an Anvil project (no pdd/ directory found in {cwd}).
   ```

   Then `raise SystemExit(1)`. Do not call `scan_project` in this branch.

2. **Scan.** Call `scan_project(Path.cwd())`. If the scanner raises `StatusScanError`, print the message as a single red Rich line and `raise SystemExit(1)` — no traceback per [conventions.md](../../../context/conventions.md) "User-facing errors: Rich-formatted, never raw tracebacks."

3. **Render three tables on a single `Console`.** Order is fixed: **Phases**, **Evals**, **Prompts**.

   - **Phases table** — columns: `Feature` (the plan's feature area), `PLAN`, `Phase`, `Prompt`, `Status`. One row per `PhaseStatus`, grouped implicitly by plan order. `Status` cell content:
     - `[green]✓ merged[/green]` when `phase.merged` is True
     - `[yellow]● prompt only[/yellow]` when prompt is on disk but not merged
     - `[dim]— not started[/dim]` — reserved for plans that have no phase prompts yet (rendered as a single dim row per plan in that case)
   - **Evals table** — columns: `Node`, `pass@1`. One row per `EvalStatus`.
     - `pass_rate is not None`: `[green]✓ {pass_rate:.0%}[/green]`
     - `pass_rate is None`: `[dim]—[/dim]`
   - **Prompts table** — columns: `Sub-agent`, `Version`, `File`. One row per `PromptStatus`. Version cell: `v{major}.{minor}.{patch}`.

4. **Empty-section contract.** If any of `status.plans`, `status.evals`, `status.prompts` is empty, render one dim row with the message `no data found at <expected path>` rather than suppressing the table. Silence on a fresh project is confusing. The "expected path" strings:
   - Phases → `pdd/prompts/features/`
   - Evals → `pdd/evals/baselines/`
   - Prompts → `anvil/prompts/sub-agents/` (or `pdd/prompts/features/sub-agents/`)

5. **Column widths.** Do not pin widths — let Rich auto-size so narrow terminals reflow cleanly.

#### Imports

```python
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from anvil.commands._status_scan import (
    PhaseStatus,
    PlanStatus,
    ProjectStatus,
    StatusScanError,
    scan_project,
)
```

(Import the names you use; do not import `EvalStatus` / `PromptStatus` if the helper functions iterate them via attribute access only.)

#### CLI wiring

No changes to [anvil/cli.py](../../../../anvil/cli.py). The existing `status_cmd() -> None` already calls `status.execute()` with no arguments — verify by reading it; do not edit.

## Acceptance

- `anvil status` in the Anvil repo prints three tables (Phases, Evals, Prompts) and exits 0. Sub-agent prompts table lists the seven sub-agents at `v1.0.0`.
- `cd /tmp && mkdir empty && cd empty && anvil status` prints `Not inside an Anvil project (no pdd/ directory found in /tmp/empty).` and exits 1.
- A project with `pdd/` but no plans / evals / prompts shows all three tables with a single dim "no data found at <path>" row each.
- No traceback ever reaches the user; both failure paths use `SystemExit(1)` after a Rich print.
- `mypy --strict anvil/commands/status.py` passes.
- No `print()` calls; only `Console.print(...)`.

## Risks

- **Narrow terminals.** Five-column Phases table can wrap. Mitigation: do not pin column widths; trust Rich's auto-sizing. The `Prompt` column (filename) is the longest cell — Rich will truncate or wrap as needed.
- **Empty-but-valid project.** A freshly-`anvil init`'d project has a `pdd/` directory but no PLANs yet — the empty-section dim rows are the *primary* UX for that state, not a corner case. Test it.
- **Per-plan grouping.** The Phases table flattens `(plan, phase)` pairs into one table; readers may want section headers. The hackathon scope is one flat table — keep the `Feature` + `PLAN` columns to disambiguate. Section headers via `rich.console.Group` is a post-demo polish item.
