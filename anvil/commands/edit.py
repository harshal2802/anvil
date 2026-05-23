"""anvil edit — conversationally extend an existing Anvil project (Tier 3)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

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
        f"[green]✓[/green] Target node detected: [bold]{target}[/bold]\n"
        f"[dim]Phase 2 wires scoped PlanScribe — coming next.[/dim]"
    )


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
