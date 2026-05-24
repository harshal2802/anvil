## Project structure

```
.
├── README.md
├── pyproject.toml
├── src
│   └── equity_agent
│       ├── __init__.py
│       ├── exceptions.py
│       ├── graph.py
│       ├── main.py
│       ├── nodes.py
│       ├── schemas.py
│       ├── services
│       │   ├── __init__.py
│       │   ├── calendar.py
│       │   └── finance.py
│       ├── state.py
│       └── utils.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── test_graph.py
    └── test_services.py
```

## Naming

- Use `snake_case` for all file names, directories, variable names, and function names.
- Use `PascalCase` for Pydantic models, LangGraph state classes, and custom exception classes.
- Use `UPPER_SNAKE_CASE` for global constants, environment variable keys, and configuration defaults.
- Prefix private helper functions with a single underscore (e.g., `_calculate_percentage_change`).

## Type hints

- Include `from __future__ import annotations` as the first line of every Python file.
- Apply strict type hints to all function signatures, class definitions, and LangGraph state fields.
- Do not use `Any` without an explicit `# type: ignore` and a documented reason.
- Define LangGraph state fields using explicit types (e.g., `list[str]` instead of `list`).

## Async

- Use `async/await` for all node definitions in LangGraph.
- Use `httpx.AsyncClient` for all external HTTP requests (e.g., macroeconomic calendar queries). Never use synchronous `httpx.Client` or `requests`.
- Execute `yfinance` calls using `asyncio.to_thread` to prevent blocking the event loop, as `yfinance` is synchronous.

## Error handling

- Define custom exceptions inheriting from a base `EquityAgentException` in `src/equity_agent/exceptions.py`.
- Wrap all `yfinance` and `httpx` network calls in `try/except` blocks that catch specific exceptions (e.g., `httpx.HTTPStatusError`, `yfinance` failure states) and raise typed custom exceptions.
- Implement a retry mechanism with exponential backoff for `httpx` requests using `tenacity` decorators.

## Logging

- Initialize a standard logger using `logging.getLogger(__name__)` at the top of each module.
- Never use `print()` statements. Use `logger.info()` for tracking execution flow and `logger.error()` for caught exceptions.
- Log all raw API payloads at the `DEBUG` level.

## Testing

- Place all tests under the `tests/` directory.
- Use `pytest` and `pytest-asyncio` for asynchronous test execution.
- Mock all external API calls (yfinance, Gemini Flash, httpx) using `unittest.mock` or `pytest-mock`. Never make real network requests during test execution.

## Anti-patterns (auto-reject in PR review)

- **Anti-pattern:** Using `datetime.now()` or `datetime.today()` directly without passing a mockable clock or dynamic provider.
- **Anti-pattern:** Hardcoding stock symbols or peer lists outside of `src/equity_agent/schemas.py` or configuration files.
- **Anti-pattern:** Using synchronous `requests` or synchronous `httpx.Client` inside LangGraph nodes.
- **Anti-pattern:** Instantiating `ChatGoogleGenerativeAI` inside a node function instead of injecting it via configuration or state.
- **Anti-pattern:** Modifying LangGraph state directly without returning the updated state dictionary from a node.
- **Anti-pattern:** Failing to validate the final output against the Pydantic schema before returning the report.