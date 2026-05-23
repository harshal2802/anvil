"""anvil status — show phase progress, eval scores, and prompt versions."""

from __future__ import annotations

from rich.console import Console

console = Console()


def execute() -> None:
    console.print("[bold cyan]anvil status[/bold cyan] — orchestrator pending.")
    console.print()
    console.print("Will read: [bold].anvil/state.json[/bold] + [bold]pdd/prompts/features/[/bold]")
    console.print("Will report:")
    console.print("  • Phases: done / in-progress / pending")
    console.print("  • Eval scores (pass@1, pass@3) per node")
    console.print("  • Prompt versions in active use")
