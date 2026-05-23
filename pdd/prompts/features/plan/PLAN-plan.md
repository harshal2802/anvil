---
name: PLAN-plan
description: Implementation plan for `anvil plan "<feature>"` — feature decomposition + one GitHub issue per phase
---

# Implementation Plan: anvil plan

**Created:** 2026-05-23
**Complexity:** Low-Medium (PlanScribe is reused verbatim; new code is mostly a `gh issue create` layer over existing scaffolding)
**Estimated phases:** 3
**Time budget:** ~75 min (~1.25 hours to demo, ~10 min buffer)

## Summary

`anvil plan "<feature>"` decomposes a single feature into 3-5 phases and opens one GitHub issue per phase, so the human reviewer can claim, schedule, and track each phase independently before `anvil run` ships PRs against those issues. The core decomposition work is already done — the existing [plan_scribe.v1.0.0.md](../sub-agents/plan_scribe.v1.0.0.md) sub-agent and its [run_plan_scribe](../../../../anvil/orchestrator/sub_agents.py) function (built for `anvil init` greenfield, see [PLAN-init-greenfield.md](../init/PLAN-init-greenfield.md)) are reused verbatim. New surface area is: (1) reading the *existing* `pdd/context/project.md` of the current Anvil project (vs init which generates it), (2) writing the `PLAN-<feature>.md` + phase-01 prompt under `pdd/prompts/features/<area>/`, and (3) a `gh issue create` loop. Per [decisions.md](../../../context/decisions.md) ("PR-per-phase, not PR-per-feature"), each phase issue is self-contained — one issue → one phase → one PR opened later by MergeBot during `anvil run`.

## Demo path

```bash
# Run from inside an Anvil-managed project (one that already has pdd/context/project.md).
anvil plan "Add a refund-eligibility node that checks order age and prior refunds"
# → writes pdd/prompts/features/refunds/PLAN-refunds.md
# → writes pdd/prompts/features/refunds/refunds-01-<phase>.md
# → opens N GitHub issues (one per phase) via `gh issue create`, labelled
#   anvil-phase + <feature_area>, with a back-reference to PLAN-<feature>.md
anvil run --phase 1   # already wired; picks up phase-01 prompt and ships a PR
```

## Runtime shape (1 Flash call, 1 wall-time step)

```
PlanScribe (reused)            step 1 (single Flash call)
      │
      └── gh issue create × N  step 2 (post-Flash, sequential subprocess loop)
```

Single Flash call — no parallelism needed. PlanScribe already emits `plan_md`, `phase_01_prompt_md`, `plan_filename`, `phase_01_filename`, and `feature_area` in one structured-output response (see [plan_scribe.v1.0.0.md](../sub-agents/plan_scribe.v1.0.0.md) response schema). Issue creation is pure `subprocess` work after the Flash call returns.

## Phases

### Phase 1: Project-context loader + CLI plumbing (no Flash)

**Produces:**
- Rewritten [anvil/commands/plan.py](../../../../anvil/commands/plan.py) — `execute(feature: str)` resolves the current Anvil-managed project root by walking up from `cwd` looking for `pdd/context/project.md`, reads it into a string, and errors cleanly with a Rich message if not found ("Run from inside an Anvil-managed project, or run `anvil init` first").
- A helper `_find_project_root(start: Path) -> Path` that walks parents; raises a typed `PlanError` if no `pdd/context/project.md` is reachable.
- A `gh` availability pre-check: shell out to `gh --version` and `gh auth status`; on failure, print a Rich error pointing the user at `brew install gh && gh auth login` and exit non-zero. Done up front so we don't pay for the Flash call before discovering `gh` is missing.
- CLI signature stays as-is in [anvil/cli.py](../../../../anvil/cli.py) (`plan_cmd` already accepts `feature: str`); no new flags this phase.

**Depends on:** nothing
**Risk:** Low — pure I/O + `subprocess` checks, mirrors the project-root pattern already used implicitly by `anvil run` against `cwd`. Watch: `gh auth status` exits non-zero on logged-out shells even when `gh` is installed — distinguish the two error messages.
**Prompt:** `pdd/prompts/features/plan/plan-01-context-loader.md`

### Phase 2: Wire PlanScribe + write artifacts (1 Flash call)

**Produces:**
- In `plan.py`, call the existing [run_plan_scribe](../../../../anvil/orchestrator/sub_agents.py) function — *verbatim, no new sub-agent prompt, no new schema*. Pass `project_md=<contents of pdd/context/project.md>`, `description=feature`, `today=date.today().isoformat()`.
- After PlanScribe returns, write two files under `<project_root>/pdd/prompts/features/<output.feature_area>/`:
  - `<output.plan_filename>` ← `output.plan_md`
  - `<output.phase_01_filename>` ← `output.phase_01_prompt_md`
- Collision policy: if the feature_area directory already exists with a `PLAN-*.md`, error and require `--force` (out of scope this phase — for now, error cleanly). Mirrors `anvil init`'s slug-collision UX.
- Rich spinner + post-call confirmation lines mirroring [commands/init.py](../../../../anvil/commands/init.py)'s style (`[green]✓[/green] PlanScribe → …`).

**Depends on:** Phase 1
**Risk:** Low — `run_plan_scribe` is shipped and tested by `anvil init`. The only new code is path construction and `Path.write_text`. Mitigation: copy the artifact-writing block from `init.py` (lines ~87-96) almost verbatim.
**Prompt:** `pdd/prompts/features/plan/plan-02-planscribe-wire.md`

### Phase 3: gh issue create loop + label conventions

**Produces:**
- A `_parse_phases(plan_md: str) -> list[PhaseRef]` helper that scans `plan_md` for `### Phase N: <name>` headings and extracts `(phase_number, phase_name)` pairs. Lightweight regex — PlanScribe's output format is fixed by its system prompt, so a strict regex is acceptable.
- A `_create_issue(...)` helper that shells out to `gh issue create --title "<title>" --label anvil-phase --label <feature_area> --body <body>`, capturing the returned issue URL. Title format: `[<feature_area>] Phase N: <name>`. Body includes: link/path to `PLAN-<area>.md`, the phase's "Produces" + "Depends on" + "Risk" lines extracted from the PLAN, and a footer "Opened by `anvil plan`".
- Sequential loop over phases (not parallel — `gh` is cheap, and ordered output is easier for the user to follow). Print each issue URL on its own line as it's created.
- Wrap each `gh issue create` in `tenacity.retry` with 3 attempts and exponential backoff per [conventions.md](../../../context/conventions.md) ("Wrap external calls … in `tenacity.retry`").
- Final Rich summary: "Opened N issues for feature `<area>`. Next: `anvil run --phase 1`."
- New typed exception `GhCliError` raised on non-zero `gh` exit; surfaces stderr in the Rich message.

**Depends on:** Phase 2
**Risk:** Medium — `gh issue create` is the first time Anvil writes to a remote service from a non-`run` command, and the failure modes (no remote configured, no write permission on the repo, rate limits) are user-environment-dependent. Mitigation: per-phase failures don't abort the loop — collect failures, print them at the end, and exit non-zero if any failed. The PLAN.md is already on disk by this point, so a user can manually re-run issue creation or open issues by hand without losing PlanScribe's output.
**Prompt:** `pdd/prompts/features/plan/plan-03-gh-issues.md`

## Risks & Unknowns

- **`gh` CLI environment variance.** Logged-out, no remote configured, wrong repo selected, rate-limited — each needs a distinct Rich error. Mitigation: the Phase 1 pre-check catches the worst cases (missing/logged-out); the Phase 3 retry-then-collect approach handles transient + per-issue failures without losing PlanScribe's work.
- **PlanScribe heading-format drift.** The Phase 3 regex assumes `### Phase N: <name>` exactly. If PlanScribe's prompt is ever updated to emit `### Phase N — <name>` or similar, issue parsing breaks silently. Mitigation: pin the format expectation in the Phase 3 prompt and add a structural test that asserts every parsed phase has a non-empty name.
- **Project root discovery from arbitrary cwd.** If the user runs `anvil plan` from a subdirectory (e.g., `src/`), Phase 1's walk-up logic must find the right `pdd/context/project.md`. Mitigation: stop the walk at the filesystem root and at `.git/` boundaries to avoid escaping into a parent repo by accident.
- **Phase count emitted by PlanScribe.** Spec says 3-5 phases — opening 5 GitHub issues per `anvil plan` call is plausible spam in a busy repo. No mitigation needed for the demo; flag for post-hackathon (`--dry-run` flag to preview issues without creating them).
- **No issue↔PR linkage yet.** This PLAN opens issues but does not yet teach MergeBot to reference them in its PR body. Mitigation: explicit out-of-scope below — that's a follow-up coupling change in MergeBot's prompt.

## Decisions resolved (logged here, not yet copied to decisions.md)

| Decision | Choice | Why |
|---|---|---|
| Reuse PlanScribe vs new sub-agent | Reuse [run_plan_scribe](../../../../anvil/orchestrator/sub_agents.py) verbatim | Identical task (project_md → phases + phase-01 prompt). New sub-agent would duplicate prompt + schema for zero benefit. Roster stays at the fixed 7 (NodeForge, EvalSmith, DocScribe, MergeBot, ProjectScribe, ConventionsScribe, PlanScribe). |
| Issue creation tool | `gh` CLI via `subprocess` | Already a project dependency (`anvil init` uses it indirectly via MergeBot's PR path; project.md tech stack lists it). Avoids adding `PyGithub`. |
| Phase issue scope | One issue per phase, labelled `anvil-phase` + `<feature_area>` | Matches "PR-per-phase" decision in [decisions.md](../../../context/decisions.md) — each issue is the reviewable unit that one MergeBot PR will close. |
| Failure mode on partial issue creation | Continue on per-issue failure, collect, exit non-zero at end | The PLAN.md is on disk already; user can recover without re-paying Flash. Aborting mid-loop would leave a confusing partial state. |

→ Copy the "Reuse PlanScribe" and "One issue per phase" rows into [pdd/context/decisions.md](../../../context/decisions.md) before Phase 3 lands — they constrain future `anvil edit` design (which per [decisions.md](../../../context/decisions.md) "Conversational `anvil edit` is composition" already plans to compose `plan` + `run`).

## Out of scope (post-demo)

- `--dry-run` flag that prints issues without calling `gh`
- `--force` to overwrite an existing `pdd/prompts/features/<area>/` tree
- Teaching MergeBot to reference the per-phase issue number in its PR body (closes #N)
- `gh repo create` if no remote is configured (today: error out)
- Issue templates per project type (CLI vs agent-graph vs data-pipeline)
- Multi-feature batch mode (`anvil plan --from features.txt`)
- Auto-assigning issues to a milestone or project board
- Detecting and amending an existing PLAN-<area>.md instead of erroring on collision
