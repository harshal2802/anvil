# Phase 3: Structural test (no Flash)

**Plan:** [PLAN-status.md](PLAN-status.md)
**Phase:** 3 of 3
**Estimated time:** ~10 min
**Dependencies:** Phase 2 ([anvil/commands/status.py](../../../../anvil/commands/status.py))
**Flash calls:** 0

## Intent

Lock the wiring of `anvil status` end-to-end with two pure-Python structural tests. The command is read-only and deterministic — no LLM-as-judge needed. The tests verify that a realistically-shaped fixture project produces a successful render containing the node name, an eval pass rate, and a sub-agent prompt version, and that an empty directory produces a Rich-formatted exit-1 error without a traceback. Both tests run unconditionally under `make test` — no `@pytest.mark.live`, no `@pytest.mark.asyncio` (`asyncio_mode = "auto"` is already set in [pyproject.toml](../../../../pyproject.toml)).

## What to build

### 1. `tests/test_status.py` (NEW)

Module docstring: one line. `from __future__ import annotations` at top. Full type hints on every signature.

#### Imports

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anvil.cli import app
```

#### Helper

`_build_fixture_project(target: Path) -> None` — under 30 lines. Creates a tree the Phase 1 scanner ([anvil/commands/_status_scan.py](../../../../anvil/commands/_status_scan.py)) can walk without complaint:

```
target/
├── pdd/
│   ├── context/project.md                              (any short body)
│   ├── prompts/features/foo/
│   │   ├── PLAN-foo.md                                 (any short body)
│   │   └── foo-01-something.md                         (any short body)
│   └── evals/baselines/foo.json                        {"pass_at_1": 0.85}
├── src/nodes/foo.py                                    (one-line stub)
└── anvil/prompts/sub-agents/node_forge.v1.0.0.md       (any short body)
```

`pass_at_1` is one of the keys `_status_scan.py` accepts; `0.85` makes the rendered cell contain an `8`. The combination of `src/nodes/foo.py` + `pdd/evals/baselines/foo.json` is what triggers the scanner's "merged" heuristic for phase 01 of `foo`.

#### Tests

1. **`test_status_renders_for_populated_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None`**
   - Build the fixture tree.
   - `monkeypatch.chdir(tmp_path)` — `CliRunner` runs in-process and `anvil/commands/status.py` calls `Path.cwd()`.
   - `result = CliRunner().invoke(app, ["status"])`.
   - Assert `result.exit_code == 0` (use `result.output` in the assertion message so failures are debuggable).
   - Assert `"foo"` in `result.output` (node name).
   - Assert a substring of the pass rate appears (e.g., `"8"` — Phase 2's exact format is `✓ 85%`, but the test stays loose so a future format tweak doesn't break it).
   - Assert the version string appears (`"1.0.0"` substring covers both `v1.0.0` and `1.0.0`).

2. **`test_status_errors_when_not_anvil_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None`**
   - `monkeypatch.chdir(tmp_path)` — empty dir, no `pdd/`.
   - `result = CliRunner().invoke(app, ["status"])`.
   - Assert `result.exit_code == 1`.
   - Assert `"Not inside"` in `result.output` (matches the Phase 2 wording `"Not inside an Anvil project..."`).
   - Assert `"Traceback (most recent call last):"` NOT in `result.output` — failures must be Rich-formatted per [pdd/context/conventions.md](../../../context/conventions.md).

## Acceptance

- `make test` runs both tests and they pass without any network or Flash calls.
- Neither test uses `@pytest.mark.live` or `@pytest.mark.asyncio`.
- `mypy --strict tests/test_status.py` passes.
- The fixture helper is under 30 lines and reads top-to-bottom — no clever abstractions.

## Risks

- **`Path.cwd()` leakage.** `CliRunner` runs in the same Python process; without `monkeypatch.chdir(tmp_path)` the command sees the developer's actual cwd. Easy to forget — both tests must call it.
- **Loose pass-rate assertion.** Asserting on `"8"` rather than `"85%"` is intentional; Phase 2 owns the exact rendering and this test only validates wiring. If Phase 2 changes the format, this test should still pass.
- **No scanner-internal tests.** This file does not unit-test `_status_scan.py` field-by-field — that is the scanner's internal contract, not a CLI concern. Add scanner-level tests in a separate file if a regression makes it necessary.
