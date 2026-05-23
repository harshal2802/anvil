# Phase 3: `--web` static HTML + SSE streaming endpoint (no Flash)

**Plan:** [PLAN-serve.md](PLAN-serve.md)
**Phase:** 3 of 4
**Estimated time:** ~30 min
**Dependencies:** Phase 1 (`build_app` + `GraphNotFoundError` in [anvil/server/app.py](../../../../anvil/server/app.py))
**Flash calls:** 0

## Intent

Turn `anvil serve --web` from a placeholder notice into a working demo surface: a single static HTML page (htmx + EventSource) served at `/`, a `/graph.json` endpoint that returns the compiled-graph topology, and a `/events` SSE endpoint that streams `astream_events(version="v2")` frames so the browser can light up nodes as they fire. Bare mode (`--web=False`) keeps its Phase-1 surface untouched — no new routes, no static mount.

## What to build

### 1. [anvil/server/web/index.html](../../../../anvil/server/web/index.html)

Single static file under ~120 lines. Loads htmx 1.9+ from a CDN (`https://unpkg.com/htmx.org@1.9.12`) — htmx is the only external dependency; CSS is inline, all custom JS is inline. A dark-theme `<style>` block defines a chat layout (input box, response area, graph SVG below). The form submits via plain JS `new EventSource("/events?input=...")` triggered by the submit handler — htmx's `hx-ext="sse"` is acceptable too, pick whichever is fewer lines. An `<svg id="graph">` placeholder is populated on page load by `fetch("/graph.json")`: each node becomes a `<g>` element, and SSE events that name a node toggle `class="active"` on the matching `<g>`. No framework, no bundler — vanilla per [decisions.md](../../../context/decisions.md) "Web UI is vanilla HTML + htmx + SSE."

### 2. [anvil/server/app.py](../../../../anvil/server/app.py) (extend `build_app`)

Extend the existing signature to `build_app(graph_module_path: Path, web: bool = False) -> FastAPI`. When `web=True`:

- Mount `/` to serve `index.html` via `FileResponse`, located through `importlib.resources.files("anvil") / "server" / "web" / "index.html"` (same pattern as [prompt_loader.py](../../../../anvil/orchestrator/prompt_loader.py)).
- `GET /graph.json` → return `json.loads(graph.get_graph().to_json())` when available; if `to_json` is missing or raises, log a `logger.warning` and return `{"nodes": [], "edges": []}` (don't crash).
- `GET /events` → query param `input` is a JSON string. Returns `text/event-stream` via `sse_starlette.sse.EventSourceResponse` wrapping an async generator that calls `async for event in graph.astream_events(json.loads(input), version="v2")` and yields `f"data: {json.dumps({'node': event.get('name'), 'event': event.get('event'), 'data': str(event.get('data', ''))[:200]})}\n\n"`. Pin to `version="v2"` per the PLAN risk note.
- Module-level constant `SSE_HEADERS: dict[str, str]` with `Cache-Control: no-cache` and `X-Accel-Buffering: no` — one-line comment explaining the *why* (proxies/htmx need these or the stream buffers and the demo looks frozen).

When `web=False`, the function returns the same FastAPI app it did in Phase 1 — no `/events`, no `/graph.json`, no static mount, no surprises for Phase 2's test.

### 3. [anvil/commands/serve.py](../../../../anvil/commands/serve.py) (wire `--web`)

- Pass `web=web` into `build_app(graph_path, web=web)`.
- Drop the Phase-1 yellow "not yet enabled" notice.
- When `web=True`, additionally log `"web UI: http://127.0.0.1:{port}/"` (via `logger.info` and a Rich line for the user).

### 4. [pyproject.toml](../../../../pyproject.toml) (package-data)

Add `"server/web/**/*"` to the `anvil = [...]` list under `[tool.setuptools.package-data]` so `index.html` ships in the wheel. One line, no other edits.

## Acceptance

- `python -c "from anvil.server.app import build_app; build_app  # noqa"` still imports cleanly, and the existing [tests/test_serve_bare.py](../../../../tests/test_serve_bare.py) still passes — the `web` parameter defaults to `False`.
- From a project with a valid `graph.py`: `anvil serve --web --port 8000` starts uvicorn, `curl localhost:8000/` returns the static HTML, `curl localhost:8000/graph.json` returns JSON with a `nodes` field, and `curl -N "localhost:8000/events?input=%7B%22messages%22%3A%5B%5D%7D"` returns `text/event-stream` with at least one `data:` frame.
- Bare `anvil serve --port 8000` (no `--web`) has none of `/`, `/graph.json`, or `/events` registered — `app.routes` introspection confirms.
- `anvil serve --web` opens [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and the page shows the graph SVG; submitting a message streams SSE frames and toggles `class="active"` on node `<g>` elements.

## Risks

- **`astream_events` schema drift.** The event dict shape (`name`, `event`, `data`) varies across LangGraph minor versions; pinning `version="v2"` keeps us on the documented surface for `langgraph>=0.2`. Don't write defensive code for older versions — the PLAN already calls this out as out-of-scope.
- **SSE buffering on proxies.** Without `Cache-Control: no-cache` and `X-Accel-Buffering: no`, nginx-style proxies and even some browser dev-tools buffer the stream and the demo looks frozen. The `SSE_HEADERS` constant exists to make this impossible to forget; the one-line comment documents the *why* per [conventions.md](../../../context/conventions.md).
- **`get_graph().to_json()` availability.** Older LangGraph compiled graphs lack `to_json`; the fallback to an empty `{"nodes": [], "edges": []}` plus a `logger.warning` keeps `--web` usable even on graphs that can't be introspected — the chat box still streams, the SVG just renders blank.
- **htmx CDN dependency.** Single network fetch on page load. Acceptable for hackathon demo; post-demo, vendor htmx into `anvil/server/web/` if offline use matters.
