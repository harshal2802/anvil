"""anvil plan — decompose a feature into phases and open GitHub issues."""

from __future__ import annotations

from rich.console import Console

console = Console()


def execute(feature: str) -> None:
    console.print("[bold cyan]anvil plan[/bold cyan] — orchestrator pending.")
    console.print(f"[dim]Feature:[/dim] {feature}")
    console.print()
    console.print("PDD workflow to be invoked: [bold]plan.md[/bold]")
    console.print("Will produce: [bold]pdd/prompts/features/<area>/PLAN-<feature>.md[/bold]")
    console.print("Will open: one GitHub issue per phase via [bold]gh issue create[/bold]")
