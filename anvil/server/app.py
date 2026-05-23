"""Build a FastAPI app that hosts the user project's compiled LangGraph via LangServe."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from langchain_core.runnables import Runnable
from langserve import add_routes

logger = logging.getLogger(__name__)


class GraphNotFoundError(RuntimeError):
    """Raised when ./graph.py is missing or does not export a `graph` symbol."""


def build_app(graph_module_path: Path) -> FastAPI:
    graph = _load_graph(graph_module_path)
    app = FastAPI(title="anvil serve", version="0.0.1")
    add_routes(app, graph, path="/invoke")
    logger.info("built FastAPI app for graph=%s", graph_module_path)
    return app


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
