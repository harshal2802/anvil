# Phase 1: Project-context loader + CLI plumbing (no Flash)

**Plan:** [PLAN-plan.md](PLAN-plan.md)
**Phase:** 1 of 3
**Estimated time:** ~20 min
**Dependencies:** none
**Flash calls:** 0

## Intent

Lay the I/O foundation for `anvil plan` before any Flash call lands. Resolve the current Anvil-managed project root by walking up from cwd looking for `pdd/context/project.md`, read it into memory for Phase 2 to consume, and pre-check that `gh` is installed and authenticated so we fail fast — not after paying for a Flash call. The CLI signature in [anvil/cli.py](../../../../anvil/cli.py) is already correct and is not touched this phase.

## What to build

### 1. [anvil/commands/plan.py](../../../../anvil/commands/plan.py)

Rewrite the 16-line stub. Public surface stays at:

```python
def execute(feature: str) -> None: ...
```

Module-local typed exception:

```python
class PlanError(Exception):
    """Raised when plan setup (project root, gh availability) fails."""
```

### 2. `_find_project_root(start: Path) -> Path` helper

Walk parents from `start` looking for `pdd/context/project.md`. Stop the walk at:

- the filesystem root (`parent == current`), AND
- any directory containing a `.git/` subdir that does NOT also contain `pdd/context/project.md` — prevents escaping into a parent repo by accident.

Raises `PlanError("No pdd/context/project.md found above {start}. Run from inside an Anvil-managed project, or run `anvil init` first.")` if the marker is never found.

```python
def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    while True:
        if (current / "pdd" / "context" / "project.md").is_file():
            return current
        if (current / ".git").is_dir():
            raise PlanError(...)  # hit a repo boundary without finding the marker
        if current.parent == current:
            raise PlanError(...)  # hit filesystem root
        current = current.parent
```

### 3. `_check_gh_available() -> None` helper

Shell out to `gh --version` and `gh auth status` via `subprocess.run(..., check=False, capture_output=True)`. Three distinct error cases:

- (a) `FileNotFoundError` from `subprocess.run` → `gh` not installed → message includes `brew install gh`.
- (b) `gh --version` succeeds but `gh auth status` returns non-zero → not authenticated → message includes `gh auth login`.
- (c) Anything else → surface `stderr.decode()` verbatim in the Rich message.

Raises `PlanError` on any failure. No return value on success.

### 4. Rewritten `execute(feature: str) -> None`

```python
def execute(feature: str) -> None:
    try:
        project_root = _find_project_root(Path.cwd())
        _check_gh_available()
        project_md = (project_root / "pdd" / "context" / "project.md").read_text(
            encoding="utf-8"
        )
    except PlanError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e

    _ = project_md  # held for Phase 2 (PlanScribe input)

    console.print(
        f"[bold cyan]anvil plan[/bold cyan] — feature: [italic]{feature}[/italic]\n"
        f"[dim]project root: {project_root}[/dim]"
    )
    console.print("[dim]Phase 2 wires PlanScribe — coming next.[/dim]")
```

Phase 2 will replace the `_ = project_md` line with the actual `run_plan_scribe` call and artifact writes. The intermediate "Phase 2 coming next" print keeps the command from appearing broken when a user runs it after Phase 1 lands but before Phase 2 does.

## Acceptance

- `anvil plan "anything"` from outside an Anvil project (no `pdd/context/project.md` reachable) prints a red Rich error and exits 1. The message mentions `anvil init`.
- `anvil plan "anything"` from inside an Anvil project with `gh` missing prints a red Rich error and exits 1. The message mentions `brew install gh`.
- `anvil plan "anything"` from inside an Anvil project with `gh` installed but logged out prints a red Rich error mentioning `gh auth login`.
- `anvil plan "anything"` from inside an Anvil project with `gh` ready prints the cyan banner with the resolved project root and the "Phase 2 coming next" dim line, exits 0.
- `from __future__ import annotations` at top; full type hints; no bare `except:`; no `print()`; one-line module docstring.

## Risks

- **`gh auth status` exit codes vary by version.** Older `gh` exits 0 on logged-out state and writes a warning to stderr. Mitigation: treat any non-empty stderr containing "not logged in" or "You are not logged" as the (b) case; otherwise rely on non-zero exit.
- **Walk-up escapes into a parent repo.** A user running `anvil plan` from inside a nested clone could find a sibling project's `project.md`. Mitigation: the `.git` boundary check above — stop at the first `.git/` that does not also have `pdd/context/project.md`.
- **`project_md` is read but unused this phase.** Acceptable: Phase 2 immediately consumes it; the `_ = project_md` placeholder is removed in Phase 2's diff. Holding it as a local rather than a module global keeps the surface clean for the Phase 2 rewrite.
