"""anvil serve — host the project's LangGraph as a FastAPI service via LangServe."""

from __future__ import annotations

import logging
from pathlib import Path

import uvicorn
from rich.console import Console

from anvil.server.app import GraphNotFoundError, build_app

logger = logging.getLogger(__name__)
console = Console()


def execute(port: int, web: bool) -> None:
    graph_path = Path.cwd() / "graph.py"

    try:
        app = build_app(graph_path)
    except GraphNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(2) from e

    if web:
        console.print(
            "[yellow]--web UI not yet enabled — coming in Phase 3. "
            "Bare LangServe endpoints (/invoke, /playground) will still serve.[/yellow]"
        )

    logger.info("anvil serve on :%d, graph=%s", port, graph_path)
    console.print(
        f"[bold cyan]anvil serve[/bold cyan] on "
        f"[bold]http://127.0.0.1:{port}[/bold] — graph=[dim]{graph_path}[/dim]"
    )
    uvicorn.run(app, host="127.0.0.1", port=port)
