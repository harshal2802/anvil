# Phase 4: Structural eval

**Plan:** [PLAN-init-greenfield.md](PLAN-init-greenfield.md)
**Phase:** 4 of 4
**Estimated time:** ~20 min
**Dependencies:** Phase 3
**Flash calls:** 1 per test invocation (real Flash, gated by pytest marker)

## Intent

One pytest that proves `anvil init` produces the expected structure end-to-end. Structural smoke test, not LLM-as-judge quality — quality evals are post-demo.

## What to build

### 1. `tests/test_init_greenfield.py`

```python
"""Structural smoke test for `anvil init` greenfield path."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anvil.cli import app


@pytest.mark.live
def test_init_greenfield_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", "Build a calculator agent that adds two numbers", "--out", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output

    # Exactly one project subdirectory created (Flash-derived slug)
    children = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(children) == 1
    project = children[0]

    # Context files present
    assert (project / "pdd" / "context" / "project.md").exists()
    assert (project / "pdd" / "context" / "conventions.md").exists()
    assert (project / "pdd" / "context" / "decisions.md").exists()

    # Git initialized + committed
    assert (project / ".git").is_dir()
    log = subprocess.check_output(["git", "log", "--oneline"], cwd=project)
    assert log.strip() != b""

    # PLAN-*.md and a phase-01 prompt exist under pdd/prompts/features/
    plans = list((project / "pdd" / "prompts" / "features").rglob("PLAN-*.md"))
    assert len(plans) >= 1
    phase_01s = list((project / "pdd" / "prompts" / "features").rglob("*-01-*.md"))
    assert len(phase_01s) >= 1

    # project.md mentions the description keyword (proves Flash got the input)
    project_md = (project / "pdd" / "context" / "project.md").read_text()
    assert "calculator" in project_md.lower()
```

### 2. [pyproject.toml](../../../../pyproject.toml)
Register the `live` marker so `pytest -m "not live"` skips cleanly in CI:

```toml
[tool.pytest.ini_options]
markers = ["live: hits real Gemini Flash — requires GOOGLE_API_KEY"]
```

## Acceptance

- `GOOGLE_API_KEY=... pytest -m live tests/test_init_greenfield.py -v` passes.
- `pytest -m "not live"` produces no warnings about unknown markers.

## Risks

- Real Flash costs a few cents per run — acceptable for hackathon.
- If `tmp_path` somehow contains a hidden `.git` from a parent worktree, the "exactly one project subdirectory" assertion would fail. `tmp_path` is pytest-managed and isolated, so this should never trigger.
