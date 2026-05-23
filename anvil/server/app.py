"""Build a FastAPI app that hosts the user project's compiled LangGraph via LangServe."""

from __future__ import annotations

import importlib.resources
import importlib.util
import json
import logging
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from langchain_core.runnables import Runnable
from langserve import add_routes
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

# Proxies (and some browsers) buffer text/event-stream without these; the demo
# looks frozen if either is missing. Keep both on every SSE response.
SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


class GraphNotFoundError(RuntimeError):
    """Raised when ./graph.py is missing or does not export a `graph` symbol."""


def build_app(graph_module_path: Path, web: bool = False) -> FastAPI:
    graph = _load_graph(graph_module_path)
    app = FastAPI(title="anvil serve", version="0.0.1")
    add_routes(app, graph, path="/invoke")
    if web:
        _mount_web(app, graph)
    logger.info("built FastAPI app for graph=%s (web=%s)", graph_module_path, web)
    return app


def _mount_web(app: FastAPI, graph: Runnable[Any, Any]) -> None:
    index_path = Path(
        str(importlib.resources.files("anvil") / "server" / "web" / "index.html")
    )

    @app.get("/", include_in_schema=False)
    async def _index() -> FileResponse:
        return FileResponse(index_path, media_type="text/html")

    @app.get("/graph.json")
    async def _graph_json() -> dict[str, Any]:
        try:
            raw = graph.get_graph().to_json()
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning("graph.get_graph().to_json() unavailable: %s", e)
            return {"nodes": [], "edges": []}
        if isinstance(raw, str):
            parsed: Any = json.loads(raw)
        else:
            parsed = raw
        if isinstance(parsed, dict):
            return parsed
        return {"nodes": [], "edges": []}

    @app.get("/events")
    async def _events(input: str = Query(...)) -> EventSourceResponse:
        payload: Any = json.loads(input)

        async def _stream() -> AsyncIterator[str]:
            async for event in graph.astream_events(payload, version="v2"):
                frame = {
                    "node": event.get("name"),
                    "event": event.get("event"),
                    "data": str(event.get("data", ""))[:200],
                }
                yield f"data: {json.dumps(frame)}\n\n"

        return EventSourceResponse(_stream(), headers=SSE_HEADERS)


def _load_graph(graph_module_path: Path) -> Runnable[Any, Any]:
    if not graph_module_path.exists():
        raise GraphNotFoundError(
            f"No graph.py found at {graph_module_path}. "
            "Run `anvil init` first, or cd into a project with a graph.py."
        )

    project_dir = str(graph_module_path.parent.resolve())
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    spec = importlib.util.spec_from_file_location("anvil_user_graph", graph_module_path)
    if spec is None or spec.loader is None:
        raise GraphNotFoundError(
            f"Could not build import spec for {graph_module_path}."
        )

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        logger.error("failed to import %s: %s", graph_module_path, e)
        raise GraphNotFoundError(
            f"Failed to import {graph_module_path}: {e}"
        ) from e

    if not hasattr(module, "graph"):
        raise GraphNotFoundError(
            f"{graph_module_path} does not export a top-level `graph` symbol. "
            "Anvil expects `graph = builder.compile()` at module scope."
        )

    graph_obj = module.graph
    if not isinstance(graph_obj, Runnable):
        raise GraphNotFoundError(
            f"{graph_module_path}.graph is not a langchain Runnable "
            f"(got {type(graph_obj).__name__}). Expected `builder.compile()` output."
        )
    return graph_obj
