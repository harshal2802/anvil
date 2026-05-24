"""anvil run — execute phase prompts via the four sub-agents.

Two modes:

1. **Per-project mode** (when a PLAN-*.md exists under
   ``pdd/prompts/features/<area>/``): load the plan, iterate the
   requested phases in order, accumulate state + existing-node
   context between phases, and finally call GraphScribe to assemble
   ``graph.py`` from every node generated so far.

2. **Smoke-test fallback** (when no plan is found): replay the
   hardcoded URL-summarization intent against phase 1 and dump
   artifacts under ``test-output/``. This preserves the original
   scaffold behavior so the demo Makefile target still works.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from rich.console import Console

from anvil.orchestrator.gemini import GeminiAuthError
from anvil.orchestrator.phase_loader import PhaseEntry, ProjectPlan, discover_plan
from anvil.orchestrator.schemas import NewStateField
from anvil.orchestrator.sub_agents import (
    GraphNodeSpec,
    GraphStateField,
    PhaseInput,
    PhaseOutput,
    forge_phase,
    run_graph_scribe,
)

console = Console()


_DEFAULT_CONVENTIONS = {
    "python_version": "3.11",
    "langgraph_version": "0.2",
    "lint": "ruff",
    "type_checker": "mypy --strict",
}


_HARDCODED_PHASE_1 = PhaseInput(
    user_intent=(
        "Fetch a URL from state and return a 3-sentence summary using the "
        "LLM client also passed via state. Handle network failures and "
        "very long pages gracefully."
    ),
    existing_nodes_json=json.dumps(
        [{"name": "load_inputs", "purpose": "reads the URL from state"}]
    ),
    state_schema_source=(
        "class GraphState(TypedDict):\n"
        "    url: str\n"
        "    summary: str | None\n"
        "    error: str | None\n"
        "    llm: object"
    ),
    repo_conventions_json=json.dumps(_DEFAULT_CONVENTIONS),
    next_adr_number="001",
)


def execute(phase: int | None, all_phases: bool) -> None:
    project_root = Path.cwd()
    plan = discover_plan(project_root)

    if plan and plan.phases:
        targets = _select_targets(plan.phases, phase, all_phases)
        if not targets:
            console.print(
                f"[yellow]No matching phase found in {plan.plan_path.name}.[/yellow]"
            )
            return
        try:
            asyncio.run(_execute_project_phases(plan, targets, project_root))
        except GeminiAuthError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(2) from e
        return

    if all_phases or phase != 1:
        console.print(
            "[yellow]No PLAN-*.md found under pdd/prompts/features/. "
            "The scaffold fallback only wires --phase 1 "
            "(hardcoded URL summarization).[/yellow]"
        )
        console.print("Run: [bold]anvil run --phase 1[/bold]")
        return

    try:
        asyncio.run(_execute_hardcoded_phase_1())
    except GeminiAuthError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(2) from e


def _select_targets(
    phases: list[PhaseEntry], phase: int | None, all_phases: bool
) -> list[PhaseEntry]:
    if all_phases:
        return list(phases)
    if phase is None:
        return [phases[0]]
    return [p for p in phases if p.number == phase]


async def _execute_project_phases(
    plan: ProjectPlan, targets: list[PhaseEntry], project_root: Path
) -> None:
    console.print(
        f"[bold cyan]anvil run[/bold cyan] — feature area "
        f"[bold]{plan.feature_area}[/bold], running "
        f"{len(targets)} phase(s): {', '.join(str(p.number) for p in targets)}\n"
    )

    existing_nodes: list[dict[str, str]] = []
    cumulative_fields: list[NewStateField] = []
    forged: list[tuple[PhaseEntry, PhaseOutput]] = []

    for entry in targets:
        console.print(
            f"[bold]Phase {entry.number}: {entry.name}[/bold] — "
            f"prompt={entry.prompt_path.name}"
        )
        phase_input = PhaseInput(
            user_intent=entry.intent,
            existing_nodes_json=json.dumps(existing_nodes or [{"name": "load_inputs", "purpose": "graph entry point"}]),
            state_schema_source=_render_state_schema(cumulative_fields),
            repo_conventions_json=json.dumps(_DEFAULT_CONVENTIONS),
            next_adr_number=f"{entry.number:03d}",
        )
        out = await forge_phase(phase_input)
        _install_phase_artifacts(out, project_root, entry.number)
        forged.append((entry, out))
        existing_nodes.append({"name": out.node.node_name, "purpose": entry.name})
        cumulative_fields = _merge_state_fields(cumulative_fields, out.node.new_state_fields)
        console.print(
            f"  [green]✓[/green] {out.node.node_name} → "
            f"src/nodes/{out.node.filename}\n"
        )

    node_specs = [
        GraphNodeSpec(
            node_name=out.node.node_name,
            import_path=f"src.nodes.{Path(out.node.filename).stem}",
            reads_from_state=list(out.node.reads_from_state),
            writes_to_state=list(out.node.writes_to_state),
        )
        for _, out in forged
    ]
    state_specs = [GraphStateField(name=f.name, type=f.type) for f in cumulative_fields]
    if not state_specs:
        state_specs = [GraphStateField(name="messages", type="list")]

    graph = await run_graph_scribe(nodes=node_specs, state_fields=state_specs)
    graph_path = project_root / "graph.py"
    graph_path.write_text(graph.graph_py_code, encoding="utf-8")
    console.print(f"[green]✓ GraphScribe → {graph_path}[/green] ({graph.notes})\n")

    _print_project_summary(forged, graph_path)


def _render_state_schema(fields: list[NewStateField]) -> str:
    if not fields:
        return "class GraphState(TypedDict):\n    pass"
    lines = ["class GraphState(TypedDict):"]
    lines.extend(f"    {f.name}: {f.type}" for f in fields)
    return "\n".join(lines)


def _merge_state_fields(
    existing: list[NewStateField], incoming: list[NewStateField]
) -> list[NewStateField]:
    by_name = {f.name: f for f in existing}
    for f in incoming:
        by_name.setdefault(f.name, f)
    return list(by_name.values())


def _install_phase_artifacts(out: PhaseOutput, project_root: Path, phase_number: int) -> None:
    """Write the phase's node, evals, ADR, and PR draft to the project root."""
    src_dir = project_root / "src"
    nodes_dir = src_dir / "nodes"
    evals_dir = project_root / "evals"
    golden_dir = evals_dir / "golden"
    adr_dir = project_root / "docs" / "adr"
    pr_dir = project_root / "pull-requests"

    for d in (nodes_dir, golden_dir, adr_dir, pr_dir):
        d.mkdir(parents=True, exist_ok=True)
    for pkg_init in (src_dir / "__init__.py", nodes_dir / "__init__.py"):
        if not pkg_init.exists():
            pkg_init.write_text("", encoding="utf-8")

    (nodes_dir / out.node.filename).write_text(out.node.module_code, encoding="utf-8")
    eval_filename = Path(out.evals.eval_runner_filename).name
    (evals_dir / eval_filename).write_text(out.evals.eval_runner_code, encoding="utf-8")
    (golden_dir / f"{out.node.node_name}.jsonl").write_text(
        out.evals.golden_dataset_jsonl, encoding="utf-8"
    )
    adr_filename = Path(out.adr.filename).name
    (adr_dir / adr_filename).write_text(out.adr.markdown_body, encoding="utf-8")
    (pr_dir / f"phase-{phase_number:02d}-pr.md").write_text(
        f"# {out.pr.pr_title}\n\nLabels: {', '.join(out.pr.labels)}\n\n"
        f"{out.pr.pr_body_markdown}\n",
        encoding="utf-8",
    )


def _print_project_summary(
    forged: list[tuple[PhaseEntry, PhaseOutput]], graph_path: Path
) -> None:
    console.print(f"[green]✓ Done.[/green] Forged {len(forged)} phase(s):\n")
    for entry, out in forged:
        console.print(
            f"  [bold]Phase {entry.number}[/bold] {entry.name} — "
            f"{out.node.node_name}: {out.pr.pr_title}"
        )
    console.print()
    console.print(f"  Graph      [dim]{graph_path}[/dim]")
    console.print(f"  Nodes      [dim]src/nodes/[/dim]")
    console.print(f"  Evals      [dim]evals/[/dim]")
    console.print(f"  ADRs       [dim]docs/adr/[/dim]")
    console.print(f"  PR drafts  [dim]pull-requests/[/dim]\n")
    console.print(f"Next: [bold]anvil serve --web[/bold]")


async def _execute_hardcoded_phase_1() -> None:
    console.print(
        "[bold cyan]anvil run --phase 1[/bold cyan] — no PLAN.md found, "
        "invoking 4 sub-agents on the URL-summarization smoke-test phase…\n"
    )
    output = await forge_phase(_HARDCODED_PHASE_1)
    out_dir = Path("test-output")
    _write_smoke_test_artifacts(output, out_dir)

    project_root = Path.cwd()
    node_module_stem = Path(output.node.filename).stem
    node_import_path = f"src.nodes.{node_module_stem}"
    _install_node_at_project_root(output, project_root)
    graph = await run_graph_scribe(
        nodes=[
            GraphNodeSpec(
                node_name=output.node.node_name,
                import_path=node_import_path,
                reads_from_state=list(output.node.reads_from_state),
                writes_to_state=list(output.node.writes_to_state),
            )
        ],
        state_fields=[
            GraphStateField(name="url", type="str"),
            GraphStateField(name="summary", type="str | None"),
            GraphStateField(name="error", type="str | None"),
            GraphStateField(name="llm", type="object"),
        ],
    )
    graph_path = project_root / "graph.py"
    graph_path.write_text(graph.graph_py_code, encoding="utf-8")
    console.print(f"[green]✓ GraphScribe → {graph_path}[/green] ({graph.notes})\n")

    _print_smoke_summary(output, out_dir)


def _install_node_at_project_root(out: PhaseOutput, project_root: Path) -> None:
    """Write the generated node under src/nodes/ at the project root so graph.py can import it."""
    src_dir = project_root / "src"
    nodes_dir = src_dir / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    for pkg_init in (src_dir / "__init__.py", nodes_dir / "__init__.py"):
        if not pkg_init.exists():
            pkg_init.write_text("", encoding="utf-8")
    (nodes_dir / out.node.filename).write_text(out.node.module_code, encoding="utf-8")


def _write_smoke_test_artifacts(out: PhaseOutput, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    node_path = root / "src" / "nodes" / out.node.filename
    eval_path = root / out.evals.eval_runner_filename
    golden_path = root / "evals" / "golden" / f"{out.node.node_name}.jsonl"
    adr_path = root / out.adr.filename
    pr_path = root / "pr.md"

    for p in (node_path, eval_path, golden_path, adr_path, pr_path):
        p.parent.mkdir(parents=True, exist_ok=True)

    node_path.write_text(out.node.module_code, encoding="utf-8")
    eval_path.write_text(out.evals.eval_runner_code, encoding="utf-8")
    golden_path.write_text(out.evals.golden_dataset_jsonl, encoding="utf-8")
    adr_path.write_text(out.adr.markdown_body, encoding="utf-8")
    pr_path.write_text(
        f"# {out.pr.pr_title}\n\nLabels: {', '.join(out.pr.labels)}\n\n"
        f"{out.pr.pr_body_markdown}\n",
        encoding="utf-8",
    )


def _print_smoke_summary(out: PhaseOutput, root: Path) -> None:
    console.print(f"[green]✓ Done.[/green] Artifacts written under [bold]{root}/[/bold]:\n")
    console.print(f"  Node       [dim]{root}/src/nodes/{out.node.filename}[/dim]")
    console.print(f"  Evals      [dim]{root}/{out.evals.eval_runner_filename}[/dim]")
    console.print(f"  Golden     [dim]{root}/evals/golden/{out.node.node_name}.jsonl[/dim]")
    console.print(f"  ADR        [dim]{root}/{out.adr.filename}[/dim]")
    console.print(f"  PR draft   [dim]{root}/pr.md[/dim]")
    console.print()
    console.print(f"[bold]PR title preview:[/bold] {out.pr.pr_title}")
    console.print(f"[bold]Node self-review:[/bold] {out.node.self_review}")
