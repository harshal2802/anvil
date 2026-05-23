"""anvil run — execute phase prompts via the four sub-agents.

For the hackathon scaffold this is a smoke test: --phase 1 runs against
a hardcoded URL-summarization intent and writes the four artifacts to
./test-output/. Real per-project phase loading lands once `anvil plan`
ships and produces real PLAN.md files.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from rich.console import Console

from anvil.orchestrator.gemini import GeminiAuthError
from anvil.orchestrator.sub_agents import PhaseInput, PhaseOutput, forge_phase

console = Console()


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
    repo_conventions_json=json.dumps(
        {
            "python_version": "3.11",
            "langgraph_version": "0.2",
            "lint": "ruff",
            "type_checker": "mypy --strict",
        }
    ),
    next_adr_number="001",
)


def execute(phase: int | None, all_phases: bool) -> None:
    if all_phases or phase != 1:
        console.print(
            "[yellow]The scaffold release only wires --phase 1 "
            "(hardcoded URL summarization).[/yellow]"
        )
        console.print("Run: [bold]anvil run --phase 1[/bold]")
        return

    try:
        asyncio.run(_execute_phase_1())
    except GeminiAuthError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(2) from e


async def _execute_phase_1() -> None:
    console.print(
        "[bold cyan]anvil run --phase 1[/bold cyan] — invoking 4 sub-agents on the "
        "URL-summarization test phase…\n"
    )
    output = await forge_phase(_HARDCODED_PHASE_1)
    out_dir = Path("test-output")
    _write_artifacts(output, out_dir)
    _print_summary(output, out_dir)


def _write_artifacts(out: PhaseOutput, root: Path) -> None:
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


def _print_summary(out: PhaseOutput, root: Path) -> None:
    console.print(f"[green]✓ Done.[/green] Artifacts written under [bold]{root}/[/bold]:\n")
    console.print(f"  Node       [dim]{root}/src/nodes/{out.node.filename}[/dim]")
    console.print(f"  Evals      [dim]{root}/{out.evals.eval_runner_filename}[/dim]")
    console.print(f"  Golden     [dim]{root}/evals/golden/{out.node.node_name}.jsonl[/dim]")
    console.print(f"  ADR        [dim]{root}/{out.adr.filename}[/dim]")
    console.print(f"  PR draft   [dim]{root}/pr.md[/dim]")
    console.print()
    console.print(f"[bold]PR title preview:[/bold] {out.pr.pr_title}")
    console.print(f"[bold]Node self-review:[/bold] {out.node.self_review}")
