---
name: PLAN-serve
description: Implementation plan for `anvil serve` — LangServe wrapper + optional htmx/SSE web UI
---

# Implementation Plan: anvil serve

**Created:** 2026-05-23
**Complexity:** Medium (no new Flash sub-agents; mostly LangServe + FastAPI plumbing + one static HTML page with SSE)
**Estimated phases:** 4
**Time budget:** ~95 min (~1h35m to demo, ~10 min buffer)

## Summary

`anvil serve [--port PORT] [--web]` hosts the current project's `graph.py` as a FastAPI service via LangServe. In **bare mode** (default), it exposes `/invoke`, `/stream`, and `/playground` on `--port` (default 8000) — a working, framework-native API for any LangGraph that follows the [templates/](../../../../anvil/templates/) shape. In **`--web` mode**, it additionally serves a single static HTML page (htmx + SSE, no build step — see [decisions.md](../../../context/decisions.md) "Web UI is vanilla HTML + htmx + SSE") at `/` for a chat box + live graph visualization that highlights nodes as they execute. Zero new Flash calls; the demo polish is entirely in static assets + a streaming endpoint.

This subcommand is the *only* one that does no Gemini work — it's the runtime surface for the artifacts that `anvil init` and `anvil run --phase 1` already produce. See [PLAN-init-greenfield.md](../init/PLAN-init-greenfield.md) for the upstream contract.

## Demo path

```bash
# In a project produced by `anvil init` (graph.py at project root)
anvil serve --port 8000
# → uvicorn on :8000, /invoke and /playground live
curl -X POST localhost:8000/invoke -d '{"input": {...}}'

# Demo polish:
anvil serve --web --port 8000
# → also serves localhost:8000/  — htmx chat box that streams graph execution
#   via SSE, with a live graph SVG that highlights each node as it fires.
```

## Runtime shape

```
anvil serve  ──►  discover ./graph.py
                      │
                      ▼
                  import graph  ── LangServe add_routes ──► FastAPI app
                                                                 │
                                       (if --web) mount static + /events SSE
                                                                 │
                                                            uvicorn run
```

No Flash calls. No sub-agents. One process, one port.

## Phases

### Phase 1: Graph discovery + module skeleton (no Flash)

**Produces:**
- New module [anvil/server/__init__.py](../../../../anvil/server/__init__.py) and [anvil/server/app.py](../../../../anvil/server/app.py) (per the project-structure tree in [conventions.md](../../../context/conventions.md) — `anvil/server/` is the documented home).
- `anvil/server/app.py` exports `build_app(graph_module_path: Path) -> FastAPI` — imports the user project's `graph.py` via `importlib.util.spec_from_file_location` (NOT `__import__`, because the project dir isn't on `sys.path`), pulls the `graph` attribute, and wraps it with `langserve.add_routes(app, graph, path="/invoke")`.
- A graph-discovery helper that locates `./graph.py` relative to cwd, with a clean error if missing: `"No graph.py found in <cwd>. Run anvil init first, or cd into a project."` — typed exception `GraphNotFoundError` per the error-handling convention in [conventions.md](../../../context/conventions.md).
- Rewrite [anvil/commands/serve.py](../../../../anvil/commands/serve.py): replace the 24-line stub with a real `execute(port, web)` that calls `build_app(...)` and `uvicorn.run(app, host="127.0.0.1", port=port)`. `--web` is wired but in this phase just logs "web UI not yet enabled" — the static page lands in Phase 3.
- Logging: `logging.getLogger(__name__)` per conventions; INFO on startup ("anvil serve on :8000, graph=<name>"), ERROR on import failure.

**Depends on:** nothing (consumes `graph.py` from the user project; doesn't need anvil init to have run *in this repo* — just any project with a `graph.py`).
**Risk:** Low-Medium. The dynamic import is the only sharp edge — user projects may have relative imports inside `graph.py` that need the project dir on `sys.path`. Mitigation: prepend the project dir to `sys.path` before importing, document it in the module docstring.
**Prompt:** `pdd/prompts/features/serve/serve-01-bare-langserve.md`

### Phase 2: Smoke test for bare mode

**Produces:**
- `tests/test_serve_bare.py` with two tests:
  1. Unit: a fixture builds a trivial `graph.py` in `tmp_path` (a one-node LangGraph that echoes its input), calls `build_app(tmp_path / "graph.py")`, asserts `/invoke` and `/playground` are registered routes on the returned FastAPI app (introspect `app.routes`). No network, no uvicorn.
  2. Negative: missing `graph.py` raises `GraphNotFoundError` with a clear message.
- Both tests are pure-Python (no Flash, no `@pytest.mark.live`), so they're safe in CI.

**Depends on:** Phase 1
**Risk:** Low. The fixture graph is throwaway — keep it under 20 lines.
**Prompt:** `pdd/prompts/features/serve/serve-02-bare-smoke-test.md`

### Phase 3: `--web` static HTML + SSE streaming endpoint

**Produces:**
- `anvil/server/web/index.html` — single static HTML file: htmx for form submission, EventSource for SSE consumption, inline `<style>` (no external CSS), an `<svg>` placeholder for the graph diagram. Loaded via `importlib.resources` so it ships in the wheel (per [conventions.md](../../../context/conventions.md) prompt-loading pattern — reuse it for static assets).
- In `anvil/server/app.py`: when `web=True`, mount `/` to serve `index.html` (FastAPI `FileResponse`) and add `/events` — an async generator endpoint that runs the graph via `graph.astream_events(...)` and yields SSE-formatted strings (`data: {json}\n\n`). Each event tags the node name so the frontend can highlight it.
- A `/graph.json` endpoint that returns the graph's node + edge structure (extract via `graph.get_graph().to_json()` or equivalent) — the HTML renders this as the static SVG, and the SSE stream toggles `class="active"` on `<g>` elements by node name.
- Wire `--web=True` end-to-end in `serve.py` so `anvil serve --web` actually serves the page.

**Depends on:** Phase 1 (Phase 2 nice-to-have but not blocking)
**Risk:** Medium. SSE + LangGraph event streaming is the load-bearing demo moment. Two specific hazards: (a) `astream_events` event names/shapes vary across LangGraph versions — pin to the `langgraph>=0.2` API surface listed in [pyproject.toml](../../../../pyproject.toml) and don't try to be version-agnostic; (b) htmx + SSE needs the right `Cache-Control: no-cache` + `X-Accel-Buffering: no` headers or proxies buffer and the demo looks broken. Mitigation: put both headers in a constant at the top of `app.py`, document the *why* per conventions.
**Prompt:** `pdd/prompts/features/serve/serve-03-web-htmx-sse.md`

### Phase 4: `--web` end-to-end manual eval

**Produces:**
- `tests/test_serve_web.py` with one `@pytest.mark.live`-style integration check (actually marked `slow`, not `live`, since there's no Flash) that:
  1. Builds the same trivial-graph fixture from Phase 2
  2. Spawns `uvicorn` in a background thread on an ephemeral port via `httpx.AsyncClient` + `asyncio`
  3. Asserts `GET /` returns the HTML with `<script src=".*htmx` in the body
  4. Asserts `GET /graph.json` returns valid JSON with a `nodes` field
  5. Asserts `GET /events?input=...` returns `text/event-stream` and at least one `data:` frame within 2s
- A short manual demo checklist in the prompt body (open `localhost:8000`, type a message, see one node light up) — this is the actual hackathon demo path and needs human eyes, not just an assertion.

**Depends on:** Phase 3
**Risk:** Low-Medium. The background-uvicorn fixture is fiddly; if it slips, fall back to TestClient (`fastapi.testclient.TestClient`) which short-circuits the network layer — SSE assertions still work over TestClient's streaming response.
**Prompt:** `pdd/prompts/features/serve/serve-04-web-eval.md`

## Risks & Unknowns

- **`graph.py` contract is implicit.** Today, [templates/](../../../../anvil/templates/) is the only documentation of what `graph.py` must export (a top-level `graph` symbol that's a compiled LangGraph). If a user-built project diverges (e.g., exports `build_graph()` instead), serve breaks. Mitigation: error message names the missing symbol explicitly; post-hackathon, formalize the contract in [conventions.md](../../../context/conventions.md).
- **LangServe + LangGraph compatibility.** LangServe's `add_routes` was designed for LCEL runnables; LangGraph compiled graphs are runnable-compatible but a few edge cases (interrupts, checkpointing) don't surface cleanly. The hackathon demo graphs are all simple linear flows, so this is fine for the demo, but document the limitation in the ADR-equivalent comment.
- **Astream-events schema drift.** As noted in Phase 3 — pin to `langgraph>=0.2` and don't write defensive code for older versions.
- **Port conflicts.** Common 8000 collision in dev. Bare uvicorn raises `OSError`; let it bubble up via the Rich-formatted error path already used in [commands/init.py](../../../../anvil/commands/init.py) for `SystemExit(2)`.
- **No reload mode.** uvicorn's `--reload` is not wired. If the demo needs live edits, document `make dev` workflow instead. Listed as out-of-scope below.

## Decisions resolved (logged here, not yet copied to decisions.md)

| Decision | Choice | Why |
|---|---|---|
| Graph discovery | Look for `./graph.py` relative to cwd, single file | Matches [templates/](../../../../anvil/templates/); avoids a config file for the hackathon |
| Dynamic import mechanism | `importlib.util.spec_from_file_location` + prepend project dir to `sys.path` | Works for projects with relative imports; doesn't require an editable install |
| Web asset packaging | `importlib.resources` against `anvil/server/web/` | Reuses the prompt-loading convention; ships in the wheel via [pyproject.toml](../../../../pyproject.toml)'s `package-data` (will need to add `server/web/**/*` to that list during Phase 3) |
| SSE endpoint shape | `/events?input=<json>` GET with `text/event-stream` | htmx + EventSource want GET; query-string input is simpler than a POST-then-SSE handshake for hackathon scope |
| Host binding | `127.0.0.1` only, not `0.0.0.0` | Local demo only; `0.0.0.0` invites firewall prompts on macOS |

→ Once Phase 3 ships, copy the "graph.py contract" decision into [pdd/context/decisions.md](../../../context/decisions.md) — it becomes a durable interface that `anvil init`'s [templates/](../../../../anvil/templates/) must honor.

## Out of scope (post-demo)

- `--reload` mode (uvicorn auto-restart on file change)
- `--host` flag for non-localhost binding
- Authentication / API keys on `/invoke`
- Multi-project serving (one anvil serve per project dir is the hackathon assumption)
- Persisting chat history across page reloads (SSE is fire-and-forget for the demo)
- Graph visualization beyond static node highlighting — no animated edges, no zoom/pan, no react-flow
- Hosted deployment (Fly.io, Render) — `anvil serve` is dev-local only for the hackathon
- Trace/observability dashboard (LangSmith integration)
- Brownfield support: serving a graph that doesn't follow the [templates/](../../../../anvil/templates/) shape
