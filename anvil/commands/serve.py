"""anvil serve — host the project's LangGraph as a FastAPI service.

Imports `graph.py` from the current project, wraps it via LangServe's
`add_routes`, and starts uvicorn. With `--web`, also serves a static
chat UI plus a live graph visualization that highlights nodes as
they execute.
"""

from __future__ import annotations

from rich.console import Console

console = Console()


def execute(port: int, web: bool) -> None:
    console.print(f"[bold cyan]anvil serve[/bold cyan] — orchestrator pending. Port: {port}, web: {web}")
    console.print()
    console.print("Will:")
    console.print("  1. Import [bold]graph.py[/bold] from the current Anvil project")
    console.print("  2. Wrap via [bold]langserve.add_routes(app, graph, path='/invoke')[/bold]")
    console.print("  3. Start uvicorn")
    if web:
        console.print("  4. Serve [bold]anvil/server/web/index.html[/bold] with live graph view")
