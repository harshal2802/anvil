# Phase 3: Wire `forge_phase` against the new phase prompt

**Plan:** [PLAN-edit.md](PLAN-edit.md)
**Phase:** 3 of 4
**Estimated time:** ~30 min
**Dependencies:** Phase 2 (scoped PlanScribe writes the phase-01 prompt + PLAN)
**Flash calls:** 3 (NodeForge → EvalSmith ∥ DocScribe → MergeBot — reused verbatim from `run.py`)

## Intent

Take the phase prompt Phase 2 just wrote and ship the edit by running the existing `forge_phase` (NodeForge → EvalSmith ∥ DocScribe → MergeBot) against it. This is the "composition not new orchestration" payoff from [decisions.md](../../../context/decisions.md) — no new sub-agents, no edit-specific Flash plumbing. The only net-new logic is project-aware artifact paths and a safe overwrite policy for the target node module.

## What to build

### 1. [anvil/commands/edit.py](../../../../anvil/commands/edit.py)

Extend `execute()` with a new async helper `_forge(project_root, phase_prompt_path, target_node, existing_nodes)`:

- Read the phase-prompt body (the file Phase 2 wrote) as `user_intent`.
- Build `existing_nodes_json`: a JSON string array of dicts `{"name": n.name, "module_path": str(n.module_path)}` for ALL existing nodes — INCLUDING the target (NodeForge needs to know this is a replacement, not a sibling). This differs from [run.py](../../../../anvil/commands/run.py)'s callsite which lists only prior nodes.
- Build `state_schema_source` by reading `<project_root>/src/state.py`. If missing, raise `EditError("<project_root>/src/state.py not found — was this project scaffolded by anvil init?")`.
- Build `repo_conventions_json` by reading `<project_root>/pdd/context/conventions.md` and wrapping it as a JSON string via `json.dumps({"conventions_md": <text>})`.
- Compute `next_adr_number`: glob `<project_root>/docs/adr/*.md`, extract the leading 3-digit number from each filename, take max + 1, format as 3-digit zero-padded string. Default `"001"` if no ADRs exist.
- Build a `PhaseInput(user_intent=…, existing_nodes_json=…, state_schema_source=…, repo_conventions_json=…, next_adr_number=…, today=date.today().isoformat())`.
- Call `output = await forge_phase(phase_input)` inside a `console.status("[bold cyan]forge_phase[/bold cyan] running NodeForge → (EvalSmith ∥ DocScribe) → MergeBot…")` spinner.
- Write artifacts back to the project (not `./test-output/`):
  - **Node:** `<project_root>/src/nodes/{output.node.filename}`. If the destination already exists, write to `{filename}.new` instead and Rich-print `[yellow]Node already exists — wrote {filename}.new instead. Diff and `mv` when ready.[/yellow]`. Otherwise write directly.
  - **Eval runner:** `<project_root>/{output.evals.eval_runner_filename}` (mkdir parents).
  - **Golden dataset:** `<project_root>/pdd/evals/baselines/{output.node.node_name}.jsonl` ← `output.evals.golden_dataset_jsonl` (mkdir parents).
  - **ADR:** `<project_root>/{output.adr.filename}` (filename already includes `docs/adr/` — mkdir parents).
- Print a final Rich summary listing all written files, the suggested PR title `output.pr.pr_title`, and a `[dim]MergeBot would open this PR — `gh pr create` wiring is post-hackathon.[/dim]` note.

Call `_forge` from `execute()` after `_scoped_plan` succeeds. Pipe the `target_node`, `existing_nodes`, and the just-written phase-prompt path through from the earlier helpers. Replace the Phase 2 placeholder line (`"Phase 3 wires forge_phase — coming next."`) with a final done message.

## Acceptance

- `_forge` raises `EditError` when `<project_root>/src/state.py` is missing — message names the file and points at `anvil init`.
- `next_adr_number` is `"001"` in a project with no ADRs and `"NNN+1"` when prior ADRs exist (e.g., `001-…md` + `002-…md` → `"003"`).
- `existing_nodes_json` includes the target node (verified by inspection in the demo run).
- When the target node file already exists, the new code lands at `<filename>.new` and the Rich note is printed; when it doesn't, the file is written directly.
- Eval runner, golden dataset, and ADR all land under their project-relative paths and parent directories are created.
- `EditError`, `GeminiAuthError`, and `GeminiResponseError` are caught at the `execute()` boundary using the same try/except shape as Phase 2 (already in place).
- `mypy --strict anvil/commands/edit.py` clean. No `print()`. Rich Console only. Typed exceptions only.

## Risks

- **`forge_phase`'s `next_adr_number` was hardcoded in `run.py`.** Edit projects have ≥1 ADR already; the glob+max+1 logic here is the right fix but is brand-new code — keep it small and obviously correct.
- **`existing_nodes_json` must include the target.** [run.py](../../../../anvil/commands/run.py)'s callsite only lists prior nodes; edit MUST include the target so NodeForge knows it's replacing logic. Flagged in the PLAN's Phase 3 risks.
- **Overwrite policy.** `.new` suffix is safer; direct overwrite is the better demo. We ship `.new` for v1 + a Rich-printed `mv` command, per the PLAN Decisions table. The eval and ADR are additive (new path / new ADR number) so they're written directly.
- **`conventions.md` size.** Wrapping a several-KB markdown file as a JSON string inflates the Flash prompt. Acceptable for v1 — NodeForge's prompt already tolerates ~5KB conventions blobs in the `run.py` callsite.
- **`gh pr create` wiring is out of scope.** MergeBot's PR text is the artifact; opening the actual PR is post-hackathon. The summary line makes this explicit so demo viewers don't expect it.

## Decisions resolved

| Decision | Choice | Why |
|---|---|---|
| Reuse `run.py`'s artifact-writing helpers vs extract to `artifacts.py` | **Copy-paste, no extraction** | `run.py`'s `_write_artifacts` is ~12 lines and writes to a flat `test-output/` root with different paths (no `.new` policy, no project-aware ADR/golden paths). Extracting would force a parametrized helper that loses clarity at both callsites. Revisit if `serve` adds a third callsite. |
| Overwrite policy for the target node module | **`.new` suffix when destination exists** | Safer first cut per the PLAN's OPEN question. Rich-print a `mv` hint. ADR and eval are additive (new path) so they're written directly. No `--force` flag in v1 — out of scope. |
