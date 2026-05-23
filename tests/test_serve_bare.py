"""Pure-Python smoke tests for `anvil/server/app.py` bare mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from anvil.server.app import GraphNotFoundError, build_app


def _write_fixture_graph(target: Path) -> None:
    target.write_text(
        "from langchain_core.runnables import RunnableLambda\n"
        "\n"
        "graph = RunnableLambda(lambda x: x)\n"
    )


def test_build_app_registers_invoke_route(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.py"
    _write_fixture_graph(graph_path)

    app = build_app(graph_path)

    paths = {getattr(route, "path", "") for route in app.routes}
    assert any(p.startswith("/invoke") for p in paths), (
        f"expected an /invoke route, got: {sorted(paths)}"
    )
    assert any("playground" in p for p in paths), (
        f"expected a playground route, got: {sorted(paths)}"
    )


def test_missing_graph_py_raises_graph_not_found_error(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.py"

    with pytest.raises(GraphNotFoundError) as excinfo:
        build_app(graph_path)

    assert "No graph.py found" in str(excinfo.value)
