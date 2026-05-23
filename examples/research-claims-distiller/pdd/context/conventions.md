## Project structure

```
.
├── README.md
├── pyproject.toml
├── src/
│   └── distiller/
│       ├── __init__.py
│       ├── main.py
│       ├── graph.py
│       ├── state.py
│       ├── nodes/
│       │   ├── __init__.py
│       │   ├── fetch.py
│       │   ├── extract.py
│       │   └── synthesize.py
│       ├── parsers.py
│       ├── schemas.py
│       └── utils.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_graph.py
    └── test_nodes.py
```

## Naming

- Use `snake_case` for all file names, directory names, function names, and variable names.
- Use `PascalCase` for all class names, including Pydantic models, LangGraph state classes, and custom exceptions.
- Use `UPPER_SNAKE_CASE` for all module-level constants.
- Suffix all LangGraph node functions with `_node` (e.g., `fetch_node`, `extract_node`).
- Suffix all Pydantic schema classes with `Schema` or `Model` (e.g., `ClaimSchema`).

## Type hints

- Write strict type hints for every function signature, variable assignment, and class field.
- Always include `from __future__ import annotations` as the very first line of every Python file.
- Use `typing.Annotated` for LangGraph state definitions to specify reducer functions.
- Never use raw `dict` or `Any` types where a Pydantic model or typed TypedDict can be used.

## Async

- Always use `async def` for all LangGraph node definitions and helper functions that perform I/O.
- Execute all HTTP requests using `async with httpx.AsyncClient() as client:` blocks.
- Set a strict, non-negotiable timeout of 10 seconds on the `httpx.AsyncClient` instance.
- Use `asyncio.gather` to execute concurrent fetches during the map phase of the graph.

## Error handling

- Wrap all HTTP operations in a `try...except httpx.HTTPError` block.
- Never let a network failure or parsing error crash the entire graph execution; catch the exception, log it, and append the failed URL to the `failed_sources` list in the state.
- Define custom exceptions inheriting from `ValueError` or a base `DistillerError` for validation failures.
- Implement a maximum of 3 retries with exponential backoff for Gemini API calls using the `google-genai` SDK's built-in retry configurations.

## Logging

- Initialize loggers using `import logging` and `logger = logging.getLogger(__name__)` at the top of each module.
- Never use the raw `print()` function for output or debugging.
- Log all network errors, API failures, and parsing warnings at the `ERROR` or `WARNING` level with full traceback context using `logger.exception()`.
- Log key state transitions and node execution steps at the `INFO` level.

## Testing

- Place all tests in the `tests/` directory, mirroring the structure of the `src/` directory.
- Use `pytest` and `pytest-asyncio` for testing asynchronous code.
- Mock all external network requests to target URLs using `pytest-mock` or `respx`; never make real HTTP requests during test execution.
- Mock all Gemini Flash API calls to return predictable, pre-defined Pydantic responses.

## Anti-patterns (auto-reject in PR review)

- Using synchronous HTTP libraries like `requests` or synchronous `httpx.Client` inside any node.
- Using raw regular expressions (`re` module) to parse or strip HTML content instead of using `beautifulsoup4`.
- Failing to include `from __future__ import annotations` at the top of any new Python file.
- Allowing a failed URL fetch to crash the graph instead of recording it in the `failed_sources` state field.
- Hardcoding the Gemini API key or any other credential instead of loading it via environment variables or Pydantic Settings.