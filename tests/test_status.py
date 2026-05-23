"""Structural tests for `anvil status` — populated project + empty-dir error path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anvil.cli import app


def _build_fixture_project(target: Path) -> None:
    pdd = target / "pdd"
    feature_dir = pdd / "prompts" / "features" / "foo"
    feature_dir.mkdir(parents=True)
    (pdd / "context").mkdir(parents=True)
    (pdd / "context" / "project.md").write_text("# Fixture project\n")
    (feature_dir / "PLAN-foo.md").write_text("# PLAN foo\n")
    (feature_dir / "foo-01-something.md").write_text("# Phase 1\n")

    nodes_dir = target / "src" / "nodes"
    nodes_dir.mkdir(parents=True)
    (nodes_dir / "foo.py").write_text("graph = None\n")

    baselines_dir = pdd / "evals" / "baselines"
    baselines_dir.mkdir(parents=True)
    (baselines_dir / "foo.json").write_text(json.dumps({"pass_at_1": 0.85}))

    sub_agents_dir = target / "anvil" / "prompts" / "sub-agents"
    sub_agents_dir.mkdir(parents=True)
    (sub_agents_dir / "node_forge.v1.0.0.md").write_text("# node_forge v1.0.0\n")


def test_status_renders_for_populated_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _build_fixture_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert "foo" in result.output, result.output
    assert "8" in result.output, result.output
    assert "1.0.0" in result.output, result.output


def test_status_errors_when_not_anvil_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code == 1, result.output
    assert "Not inside" in result.output, result.output
    assert "Traceback (most recent call last):" not in result.output, result.output
