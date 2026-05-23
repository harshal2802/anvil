# Phase 2: Smoke test for bare mode (no Flash)

**Plan:** [PLAN-serve.md](PLAN-serve.md)
**Phase:** 2 of 4
**Estimated time:** ~15 min
**Dependencies:** Phase 1 (`anvil/server/app.py` exports `build_app` and `GraphNotFoundError`)
**Flash calls:** 0

## Intent

Pin Phase 1's public surface (`build_app` + `GraphNotFoundError`) with two pure-Python tests that run under `make test` with no network, no uvicorn, and no Flash. These tests are the regression net for the only contract the rest of `anvil serve` depends on: given a `graph.py` that exports a `Runnable`, `build_app` returns a `FastAPI` app with LangServe's `/invoke` route registered; given a missing `graph.py`, it raises a typed `GraphNotFoundError` with a clear message.

## What to build

### 1. [tests/test_serve_bare.py](../../../../tests/test_serve_bare.py)

Two sync tests, both pure-Python (no `@pytest.mark.live`, no `@pytest.mark.asyncio`).

#### Test 1: `test_build_app_registers_invoke_route`

- Fixture: write a trivial `graph.py` into `tmp_path` whose module-level `graph` symbol is a `langchain_core.runnables.RunnableLambda` echoing its input (e.g., `graph = RunnableLambda(lambda x: x)`). The fixture is a small inline helper `_write_fixture_graph(target: Path) -> None` and stays under 20 lines.
- Call `build_app(tmp_path / "graph.py")`.
- Assert `/invoke` appears among `{route.path for route in app.routes}` (LangServe's `add_routes(app, graph, path="/invoke")` registers several sub-routes — at least one should start with `/invoke`).
- Optionally assert `/invoke/playground/` (or any path containing `playground`) is also registered — LangServe auto-mounts a playground UI.

#### Test 2: `test_missing_graph_py_raises_graph_not_found_error`

- Call `build_app(tmp_path / "graph.py")` against a `tmp_path` with NO `graph.py` written.
- Use `pytest.raises(GraphNotFoundError)` to capture the error.
- Assert the error message mentions `"No graph.py found"` (or equivalent substring matching Phase 1's wording).

## Acceptance

- `pytest tests/test_serve_bare.py -q` (or `make test`) passes both tests with no Flash, no network, no uvicorn.
- `ruff check tests/test_serve_bare.py` is clean.
- The fixture graph.py is generated fresh per test in `tmp_path` — no shared state across tests, no committed fixture file.
- Neither test imports `httpx`, `uvicorn`, or starts a server.
- The file opens with `from __future__ import annotations` and uses full type hints on test functions (`tmp_path: Path`).

## Risks

- **LangServe route path drift.** `add_routes` registers several paths under the given prefix (`/invoke`, `/invoke/batch`, `/invoke/stream`, `/invoke/playground/`, etc.). Asserting an exact list is brittle; assert membership of `/invoke` (or any path that *starts with* `/invoke`) instead. The playground assertion is best-effort — guard it with a flexible substring match.
- **`Runnable` instance check in `_load_graph`.** Phase 1's `_load_graph` raises `GraphNotFoundError` if `module.graph` is not a `Runnable`. The fixture must use a real `RunnableLambda` (not a plain function) or Test 1 will fail spuriously. The import is `from langchain_core.runnables import RunnableLambda`.
- **`sys.path` pollution.** Phase 1's `_load_graph` prepends `graph_module_path.parent` to `sys.path`. Across tests, multiple `tmp_path` parents accumulate. Not a correctness issue for these two tests, but worth a note for future test authors — don't add a `sys.path` cleanup fixture here; Phase 1 owns that surface.
