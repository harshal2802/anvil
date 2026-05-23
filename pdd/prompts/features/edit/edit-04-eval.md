# Phase 4: Live eval — end-to-end smoke test

**Plan:** [PLAN-edit.md](PLAN-edit.md)
**Phase:** 4 of 4
**Estimated time:** ~20 min
**Dependencies:** Phase 3 (forge wiring complete)
**Flash calls:** ~6 (one full `anvil init` + one `anvil run --phase 1` + one `anvil edit` per test invocation)

## Intent

Close the loop on `anvil edit` with one `@pytest.mark.live` structural smoke test that exercises the demo path: `anvil init` → `anvil run --phase 1` → `anvil edit "<change>"`. Same posture as [test_init_greenfield.py](../../../../tests/test_init_greenfield.py) — catches plumbing breakage (missing files, wrong paths, schema drift), NOT LLM quality. The `live` marker keeps it out of `make test`; the demo and the manual `make test-live` runner are the only callers.

## What to build

### 1. `tests/test_edit.py` (NEW)

One test function, no fixtures beyond `tmp_path` and `monkeypatch`:

```python
@pytest.mark.live
def test_edit_appends_new_phase_and_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None: ...
```

Sequence:

1. **Bootstrap** — `CliRunner().invoke(app, ["init", "Build a calculator agent that adds two numbers", "--out", str(tmp_path)])`. Assert `exit_code == 0`. Locate the single project directory under `tmp_path` and `monkeypatch.chdir(project)` so subsequent commands see it as cwd.
2. **Baseline** — `runner.invoke(app, ["run", "--phase", "1"])`. Assert `exit_code == 0`. Snapshot pre-edit counts: `*-NN-*.md` phase prompts under `pdd/prompts/features/`, ADRs under `docs/adr/`, baselines under `pdd/evals/baselines/`.
3. **Edit** — `runner.invoke(app, ["edit", "Also return the operation as a string (e.g., '2 + 3') alongside the numeric result"])`. Assert `exit_code == 0`.
4. **Structural assertions** (all liberal — Flash output is stochastic):
   - Count of `*-NN-*.md` phase prompts increased by ≥1 vs pre-edit snapshot.
   - A `PLAN-edit-*.md` file exists under some `pdd/prompts/features/<area>/`.
   - A `src/nodes/*.py.new` file exists OR a brand-new node file landed (whichever path the safe-overwrite policy from Phase 3 produced).
   - Count of `docs/adr/0??-*.md` files increased by ≥1.
   - Count of `pdd/evals/baselines/*.jsonl` files increased by ≥1.
   - No assertion on stdout text, on the QUALITY of the generated code, or on git commits — those are stochastic / out of scope.

### Imports & hygiene

```python
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from anvil.cli import app
```

Full type hints on the test signature. No `@pytest.mark.asyncio`. No `pytest.timeout` (project doesn't depend on `pytest-timeout`; the test runs ~30-60s and is invoked manually).

## Acceptance

- `pytest tests/test_edit.py -m live` runs the full bootstrap → run → edit sequence and exits 0 on a working build.
- `pytest tests/test_edit.py` (no `-m live`) collects zero tests, matching the existing `test_init_greenfield.py` convention.
- `ruff check tests/test_edit.py` clean. (mypy is not run against `tests/`.)
- A regression in `anvil edit`'s artifact writers (wrong path, missing `.new` policy, missing ADR/eval) trips at least one of the count-diff assertions.

## Risks

- **Wall time.** The test bundles ~6 Flash calls in sequence; expect 30-60s per invocation. Acceptable for a `live`-gated, manually-run check. If init latency makes the test painful in iteration, a checked-in fixture under `tests/fixtures/edit-baseline/` is the documented fallback (PLAN Phase 4 risks). Out of scope for v1.
- **Stochastic phase-prompt filenames.** PlanScribe controls the `<area>` and the phase filename. Assertions are count-diff + glob-based, never exact-name — robust to renames.
- **Overwrite vs `.new`.** Phase 3 ships `.new` when the target already exists. The eval covers BOTH outcomes (`.py.new` OR a brand-new node file) so a future "direct overwrite" policy flip doesn't break the test.
- **CI safety.** The `@pytest.mark.live` marker is the single source of truth keeping Flash-cost tests out of default CI. The marker is registered in `pyproject.toml`; do NOT change that registration here.
- **No git-commit assertion.** Edit doesn't open PRs in v1 and per-edit commits are post-hackathon. If `anvil run` or `anvil edit` happens to commit, that's fine — the test stays silent on it.
