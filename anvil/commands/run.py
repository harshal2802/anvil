"""anvil run — execute phase prompts via the four sub-agents.

For each phase: run PDD `prompts` to produce the phase prompt file, then
fan out to NodeForge / EvalSmith / DocScribe / MergeBot in parallel,
then run PDD `review` and `eval` as gates before opening the PR.
"""

from __future__ import annotations

from rich.console import Console

console = Console()


def execute(phase: int | None, all_phases: bool) -> None:
    target = "all pending phases" if all_phases else f"phase {phase}" if phase else "(none specified)"
    console.print(f"[bold cyan]anvil run[/bold cyan] — orchestrator pending. Target: {target}")
    console.print()
    console.print("Inner loop per phase:")
    console.print("  1. [bold]prompts.md[/bold] → versioned prompt file")
    console.print("  2. Four Flash sub-agents in parallel (asyncio.gather):")
    console.print("     • [bold]NodeForge[/bold] → node code")
    console.print("     • [bold]EvalSmith[/bold] → eval suite")
    console.print("     • [bold]DocScribe[/bold] → ADR")
    console.print("     • [bold]MergeBot[/bold] → PR title + body")
    console.print("  3. [bold]review.md[/bold] + [bold]eval.md[/bold] as gates")
    console.print("  4. [bold]gh pr create[/bold]")
