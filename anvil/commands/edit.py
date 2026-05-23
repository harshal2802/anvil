"""anvil edit — conversationally extend an existing Anvil project (Tier 3)."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from rich.console import Console

from anvil.orchestrator.gemini import GeminiAuthError, GeminiResponseError
from anvil.orchestrator.plan_parsing import PHASE_HEADING_RE
from anvil.orchestrator.schemas import PlanScribeOutput
from anvil.orchestrator.sub_agents import (
    PhaseInput,
    PhaseOutput,
    forge_phase,
    run_plan_scribe_scoped,
)

console = Console()


class EditError(Exception):
    """Base for anvil-edit failures."""


class NotAnAnvilProjectError(EditError):
    """cwd does not contain a pdd/context/project.md marker."""


class NoNodesFoundError(EditError):
    """src/nodes/ is missing or empty — nothing to edit yet."""


class AmbiguousTargetError(EditError):
    """Detection could not pick a single target node from the change string."""


@dataclass(frozen=True)
class NodeSummary:
    name: str
    module_path: Path


def execute(change: str) -> None:
    cwd = Path.cwd()
    try:
        project_root = _require_anvil_project(cwd)
        nodes = _enumerate_existing_nodes(project_root)
        target = _detect_target_node(change, nodes)
    except NotAnAnvilProjectError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e
    except NoNodesFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e
    except AmbiguousTargetError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e

    console.print(
        f"[bold cyan]anvil edit[/bold cyan] — change: [italic]{change}[/italic]\n"
        f"[green]✓[/green] Target node detected: [bold]{target}[/bold]"
    )

    try:
        asyncio.run(_edit_pipeline(change, project_root, target, nodes))
    except EditError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e
    except GeminiAuthError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(2) from e
    except GeminiResponseError as e:
        console.print(f"[red]Flash returned malformed output:[/red] {e}")
        raise SystemExit(2) from e


async def _edit_pipeline(
    change: str,
    project_root: Path,
    target_node: str,
    existing_nodes: list[NodeSummary],
) -> None:
    phase_prompt_path = await _scoped_plan(change, project_root, target_node)
    await _forge(project_root, phase_prompt_path, target_node, existing_nodes)


def _require_anvil_project(cwd: Path) -> Path:
    marker = cwd / "pdd" / "context" / "project.md"
    if not marker.is_file():
        raise NotAnAnvilProjectError(
            f"Not inside an Anvil project (no pdd/context/project.md found in {cwd})."
        )
    return cwd


def _enumerate_existing_nodes(project_root: Path) -> list[NodeSummary]:
    nodes_dir = project_root / "src" / "nodes"
    if not nodes_dir.is_dir():
        raise NoNodesFoundError(
            "No nodes shipped yet — run `anvil run --phase 1` first."
        )
    summaries: list[NodeSummary] = [
        NodeSummary(name=path.stem, module_path=path)
        for path in sorted(nodes_dir.glob("*.py"))
        if path.name != "__init__.py"
    ]
    if not summaries:
        raise NoNodesFoundError(
            "No nodes shipped yet — run `anvil run --phase 1` first."
        )
    return summaries


def _detect_target_node(change: str, existing_nodes: list[NodeSummary]) -> str:
    # TODO: Flash-detection expansion point — see PLAN-edit.md Decisions table.
    change_tokens = {tok for tok in re.split(r"[^a-z0-9]+", change.lower()) if tok}
    scored: list[tuple[NodeSummary, int]] = [
        (node, len(change_tokens & set(node.name.split("_"))))
        for node in existing_nodes
    ]
    top_score = max((score for _, score in scored), default=0)

    if top_score == 0:
        candidates = [node.name for node in existing_nodes]
        raise AmbiguousTargetError(_ambiguity_hint(change, candidates))

    top_nodes = [node.name for node, score in scored if score == top_score]
    if len(top_nodes) > 1:
        raise AmbiguousTargetError(_ambiguity_hint(change, top_nodes))
    return top_nodes[0]


def _ambiguity_hint(change: str, candidates: list[str]) -> str:
    return (
        f'Ambiguous — rerun as: anvil edit "{change} in <node-name>". '
        f"Candidates: {', '.join(candidates)}"
    )


async def _scoped_plan(change: str, project_root: Path, target_node: str) -> Path:
    project_md = (project_root / "pdd" / "context" / "project.md").read_text(
        encoding="utf-8"
    )
    today = date.today().isoformat()

    with console.status(
        f"[bold cyan]PlanScribe[/bold cyan] scoping plan to {target_node}…"
    ):
        output = await run_plan_scribe_scoped(
            project_md=project_md, change=change, target_node=target_node, today=today
        )

    phase_count = len(PHASE_HEADING_RE.findall(output.plan_md))
    if phase_count != 1:
        raise EditError(
            f"edit is single-node only — split the change and rerun. "
            f"PlanScribe returned {phase_count} phases."
        )

    feature_dir = project_root / "pdd" / "prompts" / "features" / output.feature_area
    feature_dir.mkdir(parents=True, exist_ok=True)

    next_nn = _next_phase_number(feature_dir)
    phase_filename = re.sub(r"-01-", f"-{next_nn:02d}-", output.phase_01_filename, count=1)
    plan_filename = f"PLAN-edit-{_slugify(change)}.md"

    phase_prompt_path = feature_dir / phase_filename
    phase_prompt_path.write_text(output.phase_01_prompt_md, encoding="utf-8")
    (feature_dir / plan_filename).write_text(output.plan_md, encoding="utf-8")

    console.print(
        f"[green]✓[/green] PlanScribe → "
        f"[dim]{output.feature_area}/{phase_filename}[/dim] + "
        f"[dim]{plan_filename}[/dim]"
    )
    _ = PlanScribeOutput  # explicit dep on the schema type for forge wiring
    return phase_prompt_path


async def _forge(
    project_root: Path,
    phase_prompt_path: Path,
    target_node: str,
    existing_nodes: list[NodeSummary],
) -> None:
    user_intent = phase_prompt_path.read_text(encoding="utf-8")

    state_path = project_root / "src" / "state.py"
    if not state_path.is_file():
        raise EditError(
            f"{state_path} not found — was this project scaffolded by anvil init?"
        )
    state_schema_source = state_path.read_text(encoding="utf-8")

    # Mirror anvil/commands/run.py's PhaseInput shape — NodeForge parses
    # specific keys, not a markdown blob. See run.py:39-46 for the contract.
    repo_conventions_json = json.dumps(
        {
            "python_version": "3.11",
            "langgraph_version": "0.2",
            "lint": "ruff",
            "type_checker": "mypy --strict",
        }
    )

    existing_nodes_json = json.dumps(
        [
            {"name": n.name, "module_path": str(n.module_path)}
            for n in existing_nodes
        ]
    )

    phase_input = PhaseInput(
        user_intent=user_intent,
        existing_nodes_json=existing_nodes_json,
        state_schema_source=state_schema_source,
        repo_conventions_json=repo_conventions_json,
        next_adr_number=_next_adr_number(project_root),
        today=date.today().isoformat(),
    )

    with console.status(
        "[bold cyan]forge_phase[/bold cyan] running NodeForge → "
        "(EvalSmith ∥ DocScribe) → MergeBot…"
    ):
        output = await forge_phase(phase_input)

    _write_forge_artifacts(project_root, output, target_node)


def _write_forge_artifacts(
    project_root: Path, output: PhaseOutput, target_node: str
) -> None:
    nodes_dir = project_root / "src" / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    node_dest = nodes_dir / output.node.filename
    if node_dest.exists():
        node_dest = nodes_dir / f"{output.node.filename}.new"
        node_dest.write_text(output.node.module_code, encoding="utf-8")
        console.print(
            f"[yellow]Node already exists — wrote {output.node.filename}.new "
            f"instead. Diff and `mv` when ready.[/yellow]"
        )
    else:
        node_dest.write_text(output.node.module_code, encoding="utf-8")

    eval_path = project_root / output.evals.eval_runner_filename
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    eval_path.write_text(output.evals.eval_runner_code, encoding="utf-8")

    golden_path = (
        project_root / "pdd" / "evals" / "baselines" / f"{output.node.node_name}.jsonl"
    )
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    golden_path.write_text(output.evals.golden_dataset_jsonl, encoding="utf-8")

    adr_path = project_root / output.adr.filename
    adr_path.parent.mkdir(parents=True, exist_ok=True)
    adr_path.write_text(output.adr.markdown_body, encoding="utf-8")

    console.print(
        f"\n[bold green]Local edit shipped[/bold green] for [bold]{target_node}[/bold] "
        f"[dim](no PR opened)[/dim]:\n"
        f"  Node       [dim]{node_dest.relative_to(project_root)}[/dim]\n"
        f"  Eval       [dim]{eval_path.relative_to(project_root)}[/dim]\n"
        f"  Golden     [dim]{golden_path.relative_to(project_root)}[/dim]\n"
        f"  ADR        [dim]{adr_path.relative_to(project_root)}[/dim]\n"
    )
    console.print(
        "[dim]Suggested PR title (MergeBot output; `gh pr create` wiring is "
        "post-hackathon):[/dim]"
    )
    console.print(f"  {output.pr.pr_title}")


def _next_adr_number(project_root: Path) -> str:
    adr_dir = project_root / "docs" / "adr"
    if not adr_dir.is_dir():
        return "001"
    numbers = [
        int(m.group(1))
        for p in adr_dir.glob("*.md")
        if (m := re.match(r"^(\d{3})", p.name))
    ]
    return f"{(max(numbers) + 1):03d}" if numbers else "001"


def _next_phase_number(feature_dir: Path) -> int:
    existing = [
        int(m.group(1))
        for p in feature_dir.glob("*-*-*.md")
        if (m := re.search(r"-(\d{2})-", p.name))
    ]
    return (max(existing) + 1) if existing else 1


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40].rstrip("-") or "change"
