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
        [
            "init",
            "Build a calculator agent that adds two numbers",
            "--out",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output

    children = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(children) == 1, f"expected one project dir, got {children}"
    project = children[0]

    assert (project / "pdd" / "context" / "project.md").exists()
    assert (project / "pdd" / "context" / "conventions.md").exists()
    assert (project / "pdd" / "context" / "decisions.md").exists()

    assert (project / ".git").is_dir()
    log = subprocess.check_output(["git", "log", "--oneline"], cwd=project)
    assert log.strip() != b""

    plans = list((project / "pdd" / "prompts" / "features").rglob("PLAN-*.md"))
    assert len(plans) >= 1
    phase_01s = list((project / "pdd" / "prompts" / "features").rglob("*-01-*.md"))
    assert len(phase_01s) >= 1

    project_md = (project / "pdd" / "context" / "project.md").read_text().lower()
    assert any(kw in project_md for kw in ("calculator", "addition", "add", "sum")), (
        f"project.md did not reference any expected keyword:\n{project_md[:500]}"
    )
