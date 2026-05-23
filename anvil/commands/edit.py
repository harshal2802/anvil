"""anvil edit — conversationally extend an existing Anvil project (Tier 3).

Structurally: `plan` + `run` chained, scoped to a single targeted change
against an already-initialized project. Composes existing workflows;
adds detection of which node(s) the change touches.
"""

from __future__ import annotations

from rich.console import Console

console = Console()


def execute(change: str) -> None:
    console.print("[bold cyan]anvil edit[/bold cyan] — orchestrator pending.")
    console.print(f"[dim]Change:[/dim] {change}")
    console.print()
    console.print("Flow: detect target node(s) → plan.md → prompts.md → 4 sub-agents → PR")
