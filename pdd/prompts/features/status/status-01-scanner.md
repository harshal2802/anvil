# Phase 1: Project scanner module (no Flash)

**Plan:** [PLAN-status.md](PLAN-status.md)
**Phase:** 1 of 3
**Estimated time:** ~20 min
**Dependencies:** none
**Flash calls:** 0

## Intent

Build the read-only filesystem scanner that `anvil status` (Phase 2) will render. One entry point — `scan_project(root: Path) -> ProjectStatus` — walks `<root>/pdd/` and `<root>/src/` once and returns a tree of frozen dataclasses covering phase progress per PLAN, eval pass rates per baseline JSON, and the highest semver per sub-agent prompt. No writes, no subprocess, no network, no Flash — pure `pathlib` + `json.loads`.

## What to build

### 1. [anvil/commands/_status_scan.py](../../../../anvil/commands/_status_scan.py) (NEW)

Module docstring: one line. `from __future__ import annotations` at top. `logger = logging.getLogger(__name__)`.

#### Frozen dataclasses (no Pydantic — there's no JSON boundary)

```python
@dataclass(frozen=True)
class PhaseStatus:
    phase_number: int
    prompt_filename: str        # e.g. "status-01-scanner.md"
    merged: bool                # evidence-based, not git-authoritative

@dataclass(frozen=True)
class PlanStatus:
    plan_filename: str          # e.g. "PLAN-status.md"
    feature_area: str           # parent directory name under features/
    phases: tuple[PhaseStatus, ...]

@dataclass(frozen=True)
class EvalStatus:
    node_name: str              # baseline JSON stem
    pass_rate: float | None     # pass_at_1 → pass_rate → None

@dataclass(frozen=True)
class PromptStatus:
    name: str                   # sub-agent slug (e.g. "node_forge")
    version: tuple[int, int, int]
    filename: str

@dataclass(frozen=True)
class ProjectStatus:
    root: Path
    plans: tuple[PlanStatus, ...]
    evals: tuple[EvalStatus, ...]
    prompts: tuple[PromptStatus, ...]
```

#### Module-local exception

```python
class StatusScanError(Exception):
    """Raised for unrecoverable scan errors. Malformed JSON is logged at DEBUG, not raised."""
```

#### `scan_project(root: Path) -> ProjectStatus`

1. **Plans/phases.** `(root / "pdd" / "prompts" / "features").rglob("PLAN-*.md")`. For each PLAN, its parent directory is the feature area. Glob siblings matching `*-[0-9][0-9]-*.md` (skip the PLAN file itself), extract the two-digit phase number from the filename, build `PhaseStatus` per phase. `merged` is True iff BOTH `<root>/src/nodes/<node>.py` AND `<root>/pdd/evals/baselines/<node>.json` exist for some `<node>` derived from the phase prompt filename — inline comment: `# evidence-based, not git-authoritative`. Use the phase prompt stem (minus the `NN-` prefix) as the `<node>` candidate.
2. **Evals.** `(root / "pdd" / "evals" / "baselines").glob("*.json")`. For each file, try `json.loads`; on `json.JSONDecodeError` log at DEBUG and skip (do not raise). Look up `pass_at_1`, then `pass_rate`, else `None`. Coerce to `float` if present.
3. **Prompts.** Prefer `<root>/anvil/prompts/sub-agents/` if it exists, else `<root>/pdd/prompts/features/sub-agents/`. Glob `*.v*.md`. Filename pattern: `<name>.vMAJOR.MINOR.PATCH.md`. Parse with a single regex; for each `<name>`, keep the highest version by tuple compare.

No I/O outside `root`. No `subprocess`. No network. No Flash. No writes.

## Acceptance

- `from anvil.commands._status_scan import scan_project, ProjectStatus` works.
- `scan_project(Path("/tmp/empty"))` returns a `ProjectStatus` with empty tuples (no exception) when `<root>/pdd/` is absent.
- `scan_project(<this repo>)` returns a `ProjectStatus` whose `prompts` includes seven sub-agents (`node_forge`, `eval_smith`, `doc_scribe`, `merge_bot`, `project_scribe`, `conventions_scribe`, `plan_scribe`) each at version `(1, 0, 0)`.
- A malformed JSON file under `pdd/evals/baselines/` is logged at DEBUG and skipped — no exception leaks out of `scan_project`.
- `mypy --strict anvil/commands/_status_scan.py` passes.
- No `print()` calls; only `logger.debug(...)` for malformed JSON.

## Risks

- **"Merged" heuristic is approximate.** A node module + baseline JSON on disk is evidence of a merged PR, not proof. Documented inline; the PLAN's "Risks & Unknowns" calls this out for reviewers.
- **Eval JSON shape is not yet locked.** EvalSmith's runner output schema is unspecified at hackathon time. Mitigation: try `pass_at_1`, then `pass_rate`, else `None` — caller renders a dim dash for missing scores.
- **Sub-agent prompt mirror.** Generated projects only have the `pdd/` copy until they run `anvil run`. Mitigation: prefer `anvil/prompts/sub-agents/` when present (the runtime mirror), fall back to `pdd/prompts/features/sub-agents/` (the source of truth) otherwise.
- **Phase-to-node mapping.** The phase prompt's stem (minus the `NN-` prefix) is a heuristic for the node name; a single phase can introduce multiple nodes. Acceptable for the hackathon; revisit when phase prompts ship a YAML front-matter `node:` field.
