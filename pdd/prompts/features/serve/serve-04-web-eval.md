# Phase 4: `--web` end-to-end eval + manual demo checklist (no Flash)

**Plan:** [PLAN-serve.md](PLAN-serve.md)
**Phase:** 4 of 4
**Estimated time:** ~20 min
**Dependencies:** Phase 3 (`build_app(..., web=True)` mounts `/`, `/graph.json`, `/events` in [anvil/server/app.py](../../../../anvil/server/app.py))
**Flash calls:** 0

## Intent

Lock down the `--web` surface with one automated integration test and a short manual demo checklist. The automated test proves the three new routes (`/`, `/graph.json`, `/events`) are actually wired and produce the expected content types — it does NOT try to validate the visual UX, that's what the manual checklist is for. Together they give us "PR-mergeable" confidence (test) plus "demo-ready" confidence (human eyes on the page).

## What to build

### 1. [tests/test_serve_web.py](../../../../tests/test_serve_web.py) — one slow integration test

A single test function `test_web_serves_html_graph_json_and_events`, marked `@pytest.mark.slow` (no `@live` — there's no Flash; no `@asyncio` — `asyncio_mode = "auto"` is already set in [pyproject.toml](../../../../pyproject.toml)).

Use `fastapi.testclient.TestClient` rather than spawning uvicorn in a background thread. Per [PLAN-serve.md](PLAN-serve.md) Phase 4 Risks, the background-uvicorn fixture is fiddly and CI-flaky; `TestClient` short-circuits the network layer and still supports streaming responses, so SSE assertions work end-to-end without binding a port.

Steps inside the test:

1. Write a trivial `graph.py` to `tmp_path` — same pattern as [tests/test_serve_bare.py](../../../../tests/test_serve_bare.py)'s `_write_fixture_graph` helper, but with `graph = RunnableLambda(lambda x: {"echo": x})` so the graph emits a non-trivial event payload through `astream_events`.
2. `app = build_app(tmp_path / "graph.py", web=True)`.
3. `client = TestClient(app)`.
4. Assert `GET /`:
   - status 200
   - `content-type` starts with `text/html`
   - body contains the substring `htmx` (proves `importlib.resources` actually located and shipped `index.html`)
5. Assert `GET /graph.json`:
   - status 200
   - body parses as JSON to a `dict`
   - dict either contains a `nodes` key OR equals the documented fallback `{"nodes": [], "edges": []}` — `RunnableLambda` has no compiled graph, so the fallback path is the expected outcome.
6. Assert `GET /events?input={"x":1}`:
   - status 200
   - `content-type` starts with `text/event-stream`
   - response body contains at least one `data:` line within a **2.0-second** wall-clock budget (`time.monotonic()` start/elapsed). Use `client.stream("GET", ...)` to consume incrementally. If no `data:` frame appears in budget, fail with a clear message.

### 2. [pyproject.toml](../../../../pyproject.toml) — register the `slow` marker

Extend the `markers = [...]` list under `[tool.pytest.ini_options]` to include `"slow: spawns uvicorn or otherwise takes >0.5s — kept separate from quick unit tests"`. Leave `asyncio_mode = "auto"` and everything else untouched.

## Acceptance

- `pytest tests/test_serve_web.py -m slow` runs the new test and it passes against the current `anvil/server/app.py`.
- `pytest -m "not slow"` does NOT run the new test (marker exclusion works).
- `ruff check tests/` is clean.
- No new top-level dependencies; `fastapi` and `langchain-core` (which provides `RunnableLambda`) are already in [pyproject.toml](../../../../pyproject.toml).

## Manual demo checklist

Pure human-eyes verification — the automated test cannot catch a broken UI. Run this once before any hackathon demo:

1. `cd` into a project produced by `anvil init` (or any directory with a valid `graph.py`).
2. `anvil serve --web --port 8000`. Expect log lines: `anvil serve on :8000, graph=...` and `web UI: http://127.0.0.1:8000/`.
3. Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in a browser. The page should render dark-themed with the title "anvil serve — live graph", a text input, a `stream` button, an empty response panel, and an SVG below containing one `<g>` per node from `graph.json`.
4. Type a valid JSON input (e.g. `{"messages": []}` for the template graph) and click `stream`. Expect:
   - The response panel begins printing one JSON frame per line as the graph executes.
   - At least one node `<g>` in the SVG toggles `class="active"` (visible as a blue-filled circle).
   - No JS errors in the browser console.
5. Submit a second message. Expect the previous stream to close cleanly (no duplicate frames), the response panel to reset, and the active-class to clear and re-light on the new run.
6. Ctrl-C the uvicorn process. Expect a clean shutdown (no stack trace).

If any of steps 3–6 fail, the bug is in [anvil/server/app.py](../../../../anvil/server/app.py) or [anvil/server/web/index.html](../../../../anvil/server/web/index.html) — the automated test only covers the contract, not the visual integration.

## Risks

- **`TestClient` + SSE.** Starlette's `TestClient` supports streaming responses via `client.stream(...)`, but some edge cases (very long-lived streams, server-side keep-alive frames) can hang. Mitigation: 2-second wall-clock budget, then fail with a clear message rather than hang the test runner. If the stream legitimately can't be consumed under `TestClient` (unlikely on current Starlette), the fallback is to assert only on status code + `content-type` and rely on the manual checklist for the data-frame check.
- **`RunnableLambda` event shape.** `astream_events` on a bare `RunnableLambda` emits `on_chain_start` / `on_chain_end` frames — not the named-node events that compiled LangGraphs emit. The test deliberately does not assert on event *names*, only that at least one `data:` line arrives. Per the PLAN, defensive coding for event-schema drift is out of scope.
- **Marker hygiene.** Adding `slow` to the markers list is mandatory — otherwise pytest emits a `PytestUnknownMarkWarning` and CI strict-warnings runs fail. The one-line registration in `pyproject.toml` is the fix.
- **No background uvicorn.** This phase deliberately does not spawn uvicorn. If a future phase needs true end-to-end network testing (e.g. proxy-behavior validation), add it in a new test file with a clear `@pytest.mark.slow` marker and an ephemeral-port fixture — don't retrofit this test.
