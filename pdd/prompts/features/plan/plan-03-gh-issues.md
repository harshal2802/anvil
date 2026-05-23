# Phase 3: gh issue create loop + label conventions

**Plan:** [PLAN-plan.md](PLAN-plan.md)
**Phase:** 3 of 3
**Estimated time:** ~30 min
**Dependencies:** Phase 2 (PlanScribe wired; `PLAN-<area>.md` already on disk)
**Flash calls:** 0

## Intent

Layer GitHub issue creation on top of the `PLAN-<area>.md` that Phase 2 just wrote, so each phase emitted by PlanScribe becomes its own reviewable, claimable unit of work in the GitHub repo. Per [decisions.md](../../../context/decisions.md) ("PR-per-phase, not PR-per-feature"), one issue maps cleanly to one MergeBot PR that `anvil run` will eventually open. The Phase 2 collision check + Flash call have already paid off — this phase is pure post-processing: parse `output.plan_md`, shell out to `gh issue create` once per phase, surface the resulting URLs, and exit non-zero if any per-issue creation failed (without losing PlanScribe's on-disk artifacts).

## What to build

### 1. Extend [anvil/commands/plan.py](../../../../anvil/commands/plan.py)

Phase 2 already shipped `PlanError`, `_find_project_root`, `_check_gh_available`, `_plan_feature` (async), and `execute()`. This phase **extends** the module — no rewrites.

Add imports at the top:

```python
import re
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential
```

### 2. New typed exception

```python
class GhCliError(PlanError):
    """Raised when `gh issue create` exits non-zero."""
```

Inherits from `PlanError` so the existing `except PlanError` block in `execute()` still catches it without a new handler arm.

### 3. `PhaseRef` frozen dataclass

```python
@dataclass(frozen=True)
class PhaseRef:
    number: int
    name: str
    body: str
```

`body` is the multi-line text under that phase heading, up to (but not including) the next `### Phase ` heading or the next `## ` heading.

### 4. `_parse_phases(plan_md: str) -> list[PhaseRef]` helper

Strict regex against PlanScribe's known format. Match `### Phase N: <name>` headings and capture the body that follows up to the next `### Phase ` or top-level `## ` heading. The regex pinned in [plan_scribe.v1.0.0.md](../sub-agents/plan_scribe.v1.0.0.md) makes this safe.

### 5. `_extract_phase_summary(phase_body: str) -> dict[str, str]` helper

Pull the `**Produces:**`, `**Depends on:**`, and `**Risk:**` lines from a phase body. Returns a dict with keys `"produces"`, `"depends_on"`, `"risk"`. Missing values become empty strings — do **not** raise. PlanScribe formatting is usually right but be forgiving (this is a stylistic excerpt, not a contract).

For `**Produces:**` (the multi-bullet block), capture from the line after the marker through the next `**...:**` marker or blank-line-then-non-bullet. The `Depends on` and `Risk` lines are single-line inline values (`**Depends on:** Phase 1`).

### 6. `_create_issue(title: str, body: str, labels: list[str]) -> str` helper

Shell out via:

```python
cmd = ["gh", "issue", "create", "--title", title, "--body", body]
for lbl in labels:
    cmd.extend(["--label", lbl])
result = subprocess.run(cmd, check=False, capture_output=True, text=True)
```

On non-zero exit: `raise GhCliError(f"gh issue create failed: {result.stderr.strip()}")`.

On success: `gh` prints the issue URL on the last non-empty line of stdout. Return that URL string.

Wrap with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)` per [conventions.md](../../../context/conventions.md). Tenacity retries on any exception by default; this is fine since `GhCliError` is the only thing this helper raises (other than programming errors that should fail loud).

### 7. Extend `_plan_feature` to run the gh loop

After the existing green confirmation line in `_plan_feature` (the `[green]✓[/green] PlanScribe → …` print), add:

1. `phases = _parse_phases(output.plan_md)`. If empty, raise `PlanError("PlanScribe emitted no parseable '### Phase N:' headings. PLAN is on disk; open issues manually.")`.
2. Build a `back_ref` string referencing the PLAN file path relative to project root: `f"From PLAN: pdd/prompts/features/{output.feature_area}/{output.plan_filename}"`.
3. Loop sequentially over phases. For each phase:
   - `summary = _extract_phase_summary(phase.body)`
   - `title = f"[{output.feature_area}] Phase {phase.number}: {phase.name}"`
   - `body` is a multi-line markdown block containing the `Produces` / `Depends on` / `Risk` excerpts (omit any section whose value is empty), the back-ref line, and a footer "Opened by `anvil plan`."
   - `labels = ["anvil-phase", output.feature_area]`
   - Try `url = _create_issue(title, body, labels)`. On success, append to `successes` and print `[green]✓[/green] #{phase.number}: {url}`.
   - On `GhCliError`, append `(phase, error)` to `failures` and continue. Print a `[yellow]⚠[/yellow]` line for the per-issue failure as it happens (so the user sees ordered output).
4. After the loop, print the green summary:

```python
console.print(
    f"\n[bold green]Opened {len(successes)} issues[/bold green] for feature "
    f"`{output.feature_area}`. Next: [bold]anvil run --phase 1[/bold]"
)
```

5. If `failures` is non-empty:
   - Print a red Rich block listing each failed phase number/name and its error message.
   - Append `f"⚠ {len(failures)} issue(s) failed — see above. PLAN is on disk; rerun `gh issue create` manually for the failed phases."`
   - `raise SystemExit(1)` AFTER the summary has been printed (so partial-success info is visible before the non-zero exit).

### 8. Update `execute()` footer

Replace the Phase 2 placeholder footer:

```python
console.print(
    "\n[bold green]Done.[/bold green] Opened the PLAN. "
    "Next: [bold]anvil plan[/bold] phase 3 (gh issues) or hand-edit the PLAN."
)
```

with:

```python
console.print(
    "\n[bold green]Done.[/bold green] PLAN + issues created. "
    "Next: [bold]anvil run --phase 1[/bold]"
)
```

The per-issue success/failure printing happens inside `_plan_feature`, so this footer only fires on a fully successful run (the `SystemExit(1)` from the failure path skips it).

## Acceptance

- Running `anvil plan "<feature>"` from inside Anvil's own project (where Phase 2 has already produced a PLAN) opens N GitHub issues — one per phase parsed from PlanScribe's `plan_md` — and prints each issue URL as it lands.
- Each created issue carries the labels `anvil-phase` and `<feature_area>`, has a title of the form `[<feature_area>] Phase N: <name>`, and includes the per-phase Produces/Depends/Risk excerpts plus the back-reference to `PLAN-<area>.md`.
- If `gh issue create` fails for a single phase (e.g., flaky network, label missing), the loop continues, the failure is reported at the end in red, and the command exits 1. The remaining phases still get issues.
- If `gh issue create` fails 3 times in a row for the same phase (tenacity exhaustion), that phase is recorded as a single failure and the loop moves on.
- `_parse_phases("")` returns `[]` and the caller raises `PlanError` cleanly (no `IndexError`, no Flash re-pay).
- `from __future__ import annotations` retained; full type hints; `mypy --strict` clean; no bare `except:`; no `print()`; no multi-paragraph docstrings.

## Risks

- **`gh issue create` label requirement.** GitHub repos do not have a label called `anvil-phase` by default; passing `--label anvil-phase` on a repo without that label fails with `could not add label: 'anvil-phase' not found`. Mitigation for the demo: rely on the user's repo having had the label pre-created, OR document the one-time `gh label create anvil-phase` step in the PLAN follow-up. Out of scope for this phase to auto-create labels.
- **Last-non-empty-line parsing.** `gh issue create` usually prints just the issue URL, but some versions print a trailing newline or interstitial text. Walk stdout's lines in reverse and return the first non-empty one — strict equality matching would over-fit a single `gh` version.
- **PlanScribe heading drift.** If `### Phase N: <name>` ever becomes `### Phase N — <name>` or similar, `_parse_phases` returns `[]` and the helpful error fires. Acceptable: PlanScribe's system prompt pins the format, and the empty-return case is handled.
- **Per-issue retry vs whole-loop retry.** Tenacity wraps `_create_issue` per call, so each phase gets its own 3-attempt budget. A wholly broken `gh auth` would burn 3N attempts before reporting — but Phase 1's `_check_gh_available()` already catches that case at startup, so this is purely belt-and-suspenders.
