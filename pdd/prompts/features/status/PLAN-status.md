---
name: PLAN-status
description: Implementation plan for `anvil status` — read-only project dashboard
---

# Implementation Plan: anvil status

**Created:** 2026-05-23
**Complexity:** Low (read-only filesystem scan + Rich table render, no Flash calls)
**Estimated prompts:** 3
**Time budget:** ~45 min (smallest subcommand on the roadmap)

## Summary

`anvil status` is a read-only dashboard for an Anvil-generated project. It walks the project's `pdd/` and `src/` trees, derives three views — phase progress per `PLAN-*.md`, eval pass rates from `pdd/evals/baselines/*.json`, and the highest version per sub-agent prompt — and prints them as Rich tables. No Flash calls, no writes, no network. It is the inverse of [anvil/commands/init.py](../../../../anvil/commands/init.py) and [anvil/commands/run.py](../../../../anvil/commands/run.py): those produce the artifacts this command observes. The contract is strictly observational; per [decisions.md](../../../context/decisions.md) the orchestrator never lives in read-only commands, so status owns its own small scanner module under `anvil/commands/`.

## Demo path

```bash
cd customer-support-agent          # a project previously created by anvil init
anvil status
# → three Rich tables:
#   1. Phases    — PLAN file × phase index → {prompt? merged? eval passing?}
#   2. Evals     — node name → pass@1 from baselines/<node>.json
#   3. Prompts   — sub-agent name → highest semver found under anvil/prompts/sub-agents/
```

## Runtime shape (0 Flash calls, pure filesystem)

```
scan_project()                              step 1 (sequential — single pass over pdd/ + src/)
      │
      ▼
render_tables()                             step 2 (pure Rich rendering)
```

Status is offline by design — no `asyncio`, no `google-genai`, no `gh`. The whole command is synchronous Python over `pathlib`.

## Phases

### Phase 1: Project scanner module

**Produces:**
- New module `anvil/commands/_status_scan.py` exposing one entry point `scan_project(root: Path) -> ProjectStatus` plus dataclasses `ProjectStatus`, `PlanStatus`, `PhaseStatus`, `EvalStatus`, `PromptStatus` (frozen `@dataclass`es, no Pydantic — there's no JSON boundary).
- Logic:
  - Find `PLAN-*.md` files under `pdd/prompts/features/**/`. For each, glob sibling `*-NN-*.md` phase prompts to determine which phase numbers have a prompt on disk.
  - For each phase, mark "merged" if a corresponding node module exists under `src/nodes/` AND a `pdd/evals/baselines/<node>.json` exists. Heuristic, not authoritative — the contract is "evidence on disk," not git history.
  - Read each `pdd/evals/baselines/*.json` (skip silently if malformed — log at DEBUG) and pull a `pass_rate` / `pass_at_1` field. The exact key is loose: try `pass_at_1`, then `pass_rate`, then None.
  - Glob `anvil/prompts/sub-agents/*.v*.md` (look in the *project's* anvil-prompts mirror if present, else fall back to the canonical `pdd/prompts/features/sub-agents/`) and parse the `vMAJOR.MINOR.PATCH` suffix per [conventions.md](../../../context/conventions.md). For each sub-agent name, keep the highest version by tuple compare.
- No I/O outside the passed `root` directory; no `subprocess`; no network. `mypy --strict` clean.

**Depends on:** nothing
**Risk:** Low — pure `pathlib` + `json.loads`. The only sharp edge is the "merged" heuristic; document it inline as "evidence-based, not authoritative" so reviewers don't expect git introspection.
**Prompt:** `pdd/prompts/features/status/status-01-scanner.md`

### Phase 2: Rich rendering + command wiring

**Produces:**
- [anvil/commands/status.py](../../../../anvil/commands/status.py) rewritten — the current 17-line stub becomes a real `execute()` that calls `scan_project(Path.cwd())` and renders three `rich.table.Table` instances on a single `Console`. Order: Phases, Evals, Prompts. Empty sections render a dim "no data found at <path>" row rather than being suppressed — silence on a fresh project is confusing.
- Color contract (consistent with [anvil/commands/init.py](../../../../anvil/commands/init.py) and [anvil/commands/run.py](../../../../anvil/commands/run.py)):
  - green check for merged phases / passing evals
  - yellow dot for prompt-on-disk-but-no-code
  - dim dash for not-yet-started
- Graceful failure path: if `pdd/` is not present in cwd, print one Rich line — `"Not inside an Anvil project (no pdd/ directory found in {cwd})."` — and `raise SystemExit(1)`. No traceback, per [conventions.md](../../../context/conventions.md) "User-facing errors: Rich-formatted, never raw tracebacks."
- No changes to [anvil/cli.py](../../../../anvil/cli.py) — the existing `status_cmd` signature `() -> None` is already correct.

**Depends on:** Phase 1
**Risk:** Low — Rich tables are a well-trodden path. Watch: column widths on narrow terminals; let Rich auto-size, do not pin widths.
**Prompt:** `pdd/prompts/features/status/status-02-render.md`

### Phase 3: Structural test

**Produces:** `tests/test_status.py` with two unit tests (no `@pytest.mark.live` — status has no Flash calls, so CI runs it unconditionally):
1. Fixture builds a fake project tree in `tmp_path` with one `PLAN-foo.md`, one phase prompt, one node module, one baseline JSON, and one sub-agent prompt. Invokes the Typer app via `CliRunner` and asserts: exit code 0, the node name appears in stdout, the pass rate appears in stdout, the highest version string appears in stdout.
2. Same `CliRunner` invocation in an empty `tmp_path` asserts exit code 1 and the "Not inside an Anvil project" message.

Not an LLM-as-judge eval — there is no stochastic output to judge. Structural assertions are sufficient and correct for a read-only command.

**Depends on:** Phase 2
**Risk:** Low. Watch: `CliRunner` runs in the same process, so `Path.cwd()` must be patched (`monkeypatch.chdir(tmp_path)`) — easy to forget.
**Prompt:** `pdd/prompts/features/status/status-03-test.md`

## Risks & Unknowns

- **"Merged" heuristic is approximate.** A node module + baseline JSON on disk is evidence of a merged PR, but a partially-applied phase could trip a false positive. Accept this for the hackathon; a post-demo upgrade can read `git log --grep="phase N"` for ground truth.
- **Eval JSON shape is not yet locked.** EvalSmith writes `evals/test_<node>.py` runner code, but the *output* schema of running that runner (the baseline JSON written to `pdd/evals/baselines/`) is not yet specified anywhere. Phase 1 tolerates this by trying multiple keys and falling back to `None`. If the eval-baseline schema lands during the hackathon, tighten the parser then.
- **Prompt mirror location.** Per [conventions.md](../../../context/conventions.md), sub-agent prompts live at both `pdd/prompts/features/sub-agents/` and `anvil/prompts/sub-agents/`. Generated projects only have the `pdd/` copy until they run `anvil run` against a node that adds an anvil-prompts mirror. Phase 1 must prefer the `pdd/` copy as the source of truth.
- **No state file.** The existing stub mentions `.anvil/state.json` — that file is aspirational and has no writer. This PLAN deliberately does NOT introduce one; everything is derived from on-disk artifacts so there's no second source of truth to keep in sync.

## Decisions resolved (logged here, not yet copied to decisions.md)

| Decision | Choice | Why |
|---|---|---|
| Source of truth for phase status | Filesystem scan, not a state file | One source of truth; resilient to manual edits; no writer to maintain |
| "Merged" detection | Heuristic: node module + baseline JSON both present | Cheap, evidence-based; git introspection is post-demo |
| Output format | Three Rich tables on stdout, no `--json` flag | Smallest demo surface; structured output is post-demo |
| Failure when cwd is not an Anvil project | Exit 1 with single Rich-formatted line | Matches `commands/` error-UX convention; no traceback |

→ Promote the "filesystem-is-source-of-truth" decision into [pdd/context/decisions.md](../../../context/decisions.md) after Phase 1 lands — it constrains every future read-only command (`anvil plan --show`, eventual `anvil drift`, etc.).

## Out of scope (post-demo)

- `--json` / `--yaml` machine-readable output modes
- `--watch` mode that re-renders on filesystem changes
- Git-aware merge detection (`git log --grep` for phase numbers)
- Drift detection between `pdd/prompts/features/sub-agents/` and `anvil/prompts/sub-agents/`
- Eval trend lines (current pass@1 vs the previous baseline)
- Cross-project rollup (`anvil status --all` over a directory of projects)
- Color-blind palette / `--no-color` (Rich already respects `NO_COLOR` env var)
