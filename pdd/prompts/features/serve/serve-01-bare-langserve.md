# Phase 1: Graph discovery + bare LangServe (no Flash)

**Plan:** [PLAN-serve.md](PLAN-serve.md)
**Phase:** 1 of 4
**Estimated time:** ~25 min
**Dependencies:** none (consumes a user project's `graph.py` at runtime; doesn't require `anvil init` in this repo)
**Flash calls:** 0

## Intent

Stand up the `anvil/server/` module and rewrite the `anvil serve` command stub into a real entry point that imports the user project's `graph.py`, wraps it via LangServe, and serves it on uvicorn. `--web` is wired through the CLI but only logs a "coming in Phase 3" notice — the static HTML + SSE work is deferred. This phase delivers the framework-native API surface (`/invoke`, `/playground`) that the rest of the demo builds on.

## What to build

### 1. [anvil/server/__init__.py](../../../../anvil/server/__init__.py)

One-line module docstring marking the package. `from __future__ import annotations`. Nothing else — keep the public surface in `app.py`.

### 2. [anvil/server/app.py](../../../../anvil/server/app.py)

Public surface:

```python
def build_app(graph_module_path: Path) -> FastAPI: ...

class GraphNotFoundError(RuntimeError): ...
```

- Use `importlib.util.spec_from_file_location("anvil_user_graph", graph_module_path)` to dynamically import the user project's `graph.py` (NOT `__import__`, because the project dir isn't on `sys.path`).
- Before calling `spec.loader.exec_module(module)`, prepend `graph_module_path.parent` (resolved absolute) to `sys.path` so relative imports inside `graph.py` (e.g., `from .nodes import ...`) resolve cleanly.
- Pull the `graph` attribute off the loaded module and wrap it with `langserve.add_routes(app, graph, path="/invoke")` on a freshly constructed `FastAPI(title="anvil serve", ...)`.
- Raise the typed `GraphNotFoundError` with a clear message in three failure cases:
  1. `graph.py` doesn't exist at the given path → `"No graph.py found at <path>. Run anvil init first, or cd into a project with a graph.py."`
  2. The spec/loader can't be constructed.
  3. The imported module has no top-level `graph` attribute.
- Catch the user-import `Exception` only to re-raise as `GraphNotFoundError` with context (this is the one place a bare `Exception` catch is justified — it's a boundary for arbitrary third-party code). Log at ERROR before re-raising.
- `logger = logging.getLogger(__name__)`. INFO on successful build with the graph path.

### 3. [anvil/commands/serve.py](../../../../anvil/commands/serve.py)

Replace the 24-line stub. Public surface unchanged:

```python
def execute(port: int, web: bool) -> None: ...
```

- Compute `graph_path = Path.cwd() / "graph.py"`.
- Call `build_app(graph_path)`. On `GraphNotFoundError`, print red via Rich and `raise SystemExit(2)` — mirror the pattern in [anvil/commands/init.py](../../../../anvil/commands/init.py) for `GeminiAuthError`.
- If `web=True`, print a yellow Rich notice: "--web UI not yet enabled — coming in Phase 3." Do NOT mount any static routes; bare LangServe endpoints still serve.
- INFO log "anvil serve on :PORT, graph=PATH" before starting uvicorn.
- `uvicorn.run(app, host="127.0.0.1", port=port)` — bind to localhost only per the PLAN's Decisions table (no `0.0.0.0`).

## Acceptance

- `anvil serve --help` shows `--port` and `--web` (already wired in `cli.py`; no CLI change in this phase).
- From a directory with a valid `graph.py` exporting a compiled LangGraph: `anvil serve --port 8000` starts uvicorn on `127.0.0.1:8000`, and `curl localhost:8000/invoke/playground/` returns the LangServe playground HTML.
- From a directory without `graph.py`: `anvil serve` prints a red Rich error naming the missing path and exits with code 2.
- `anvil serve --web` prints the "not yet enabled" yellow notice but still serves bare endpoints — does NOT crash, does NOT 404 on `/`.
- `python -c "from anvil.server.app import build_app, GraphNotFoundError"` imports cleanly with no side effects.

## Risks

- **Dynamic-import sharp edge.** User `graph.py` files may do relative imports (`from .nodes import x`). Mitigation: prepend the project dir to `sys.path` before `exec_module`, document the *why* in a one-line comment inside `_load_graph`.
- **`graph.py` contract is implicit.** If a user project exports `build_graph()` or `app` instead of `graph`, serve fails with the typed error — acceptable for the hackathon; post-demo, formalize in [conventions.md](../../../context/conventions.md). The PLAN already tracks this in Risks & Unknowns.
- **Port 8000 collision.** uvicorn raises `OSError` on bind failure; let it bubble — the user sees a clear traceback. Don't wrap in a try/except just to reformat the message.
- **Boundary `Exception` catch.** `_load_graph` is the one place we catch a bare `Exception` to re-raise as `GraphNotFoundError`. This is intentional (user code is arbitrary) and is the only `# noqa`-style exemption justified by conventions.md's "if you catch, you log and re-raise or transform" rule.
