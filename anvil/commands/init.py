"""anvil init — scaffold a new project (greenfield) or retrofit PDD (brownfield).

Greenfield: routes to the PDD `scaffold` workflow, then `context`, then `plan`.
Brownfield (--existing): routes to the PDD `init` workflow with detection
and user confirmation before any files are written.
"""

from __future__ import annotations

from rich.console import Console

console = Console()


def execute(description: str, existing: bool = False) -> None:
    mode = "brownfield" if existing else "greenfield"
    console.print(f"[bold cyan]anvil init[/bold cyan] ({mode}) — orchestrator pending.")
    console.print(f"[dim]Description:[/dim] {description}")
    console.print()
    console.print("Next milestone: [bold]anvil/orchestrator/stages.py[/bold]")
    console.print(
        "PDD workflow to be invoked: "
        f"[bold]{'init.md' if existing else 'scaffold.md'} → context.md → plan.md[/bold]"
    )
