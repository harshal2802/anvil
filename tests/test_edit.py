"""Structural smoke test for `anvil edit` — init → run → edit pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from anvil.cli import app


@pytest.mark.live
def test_edit_appends_new_phase_and_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()

    init_result = runner.invoke(
        app,
        [
            "init",
            "Build a calculator agent that adds two numbers",
            "--out",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0, init_result.output

    children = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(children) == 1, f"expected one project dir, got {children}"
    project = children[0]

    monkeypatch.chdir(project)

    run_result = runner.invoke(app, ["run", "--phase", "1"])
    assert run_result.exit_code == 0, run_result.output

    features_root = project / "pdd" / "prompts" / "features"
    adr_root = project / "docs" / "adr"
    baselines_root = project / "pdd" / "evals" / "baselines"

    pre_phase_prompts = list(features_root.rglob("*-[0-9][0-9]-*.md"))
    pre_adrs = list(adr_root.glob("0??-*.md")) if adr_root.is_dir() else []
    pre_baselines = (
        list(baselines_root.glob("*.jsonl")) if baselines_root.is_dir() else []
    )

    edit_result = runner.invoke(
        app,
        [
            "edit",
            "Also return the operation as a string (e.g., '2 + 3') alongside the numeric result",
        ],
    )
    assert edit_result.exit_code == 0, edit_result.output

    post_phase_prompts = list(features_root.rglob("*-[0-9][0-9]-*.md"))
    assert len(post_phase_prompts) >= len(pre_phase_prompts) + 1, (
        f"expected a new phase prompt; pre={len(pre_phase_prompts)} "
        f"post={len(post_phase_prompts)}"
    )

    plan_edit_files = list(features_root.rglob("PLAN-edit-*.md"))
    assert plan_edit_files, "expected a PLAN-edit-*.md under pdd/prompts/features/"

    nodes_dir = project / "src" / "nodes"
    new_suffix_nodes = list(nodes_dir.glob("*.py.new"))
    all_nodes = [p for p in nodes_dir.glob("*.py") if p.name != "__init__.py"]
    assert new_suffix_nodes or len(all_nodes) >= 2, (
        f"expected a *.py.new artifact or a brand-new node file; "
        f"new={new_suffix_nodes} all={all_nodes}"
    )

    post_adrs = list(adr_root.glob("0??-*.md")) if adr_root.is_dir() else []
    assert len(post_adrs) >= len(pre_adrs) + 1, (
        f"expected a new ADR; pre={len(pre_adrs)} post={len(post_adrs)}"
    )

    post_baselines = (
        list(baselines_root.glob("*.jsonl")) if baselines_root.is_dir() else []
    )
    assert len(post_baselines) >= len(pre_baselines) + 1, (
        f"expected a new eval baseline jsonl; "
        f"pre={len(pre_baselines)} post={len(post_baselines)}"
    )
