"""Integration test for `anvil/server/app.py` --web mode via FastAPI TestClient."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from anvil.server.app import build_app


def _write_fixture_graph(target: Path) -> None:
    target.write_text(
        "from langchain_core.runnables import RunnableLambda\n"
        "\n"
        "graph = RunnableLambda(lambda x: {\"echo\": x})\n"
    )


@pytest.mark.slow
def test_web_serves_html_graph_json_and_events(tmp_path: Path) -> None:
    """Exercise /, /graph.json, and /events through TestClient.

    Uses TestClient rather than a background uvicorn thread per PLAN-serve.md
    Phase 4 Risks — short-circuits the network layer, still streams SSE.
    """
    graph_path = tmp_path / "graph.py"
    _write_fixture_graph(graph_path)

    app = build_app(graph_path, web=True)
    client = TestClient(app)

    index = client.get("/")
    assert index.status_code == 200
    assert index.headers["content-type"].startswith("text/html")
    assert "htmx" in index.text

    gj = client.get("/graph.json")
    assert gj.status_code == 200
    data = gj.json()
    assert isinstance(data, dict)
    assert "nodes" in data or data == {"nodes": [], "edges": []}

    payload = json.dumps({"x": 1})
    deadline = 2.0
    start = time.monotonic()
    saw_data_line = False
    with client.stream("GET", "/events", params={"input": payload}) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        for line in resp.iter_lines():
            if time.monotonic() - start > deadline:
                break
            text = line if isinstance(line, str) else line.decode("utf-8", "replace")
            if text.startswith("data:"):
                saw_data_line = True
                break

    elapsed = time.monotonic() - start
    assert saw_data_line, (
        f"no `data:` SSE frame within {deadline}s (elapsed={elapsed:.2f}s)"
    )
