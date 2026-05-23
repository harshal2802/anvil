# Conventions

## Project structure

```
anvil/
├── anvil/                       Python package
│   ├── cli.py                   Typer entry point
│   ├── commands/                One file per subcommand; each has execute()
│   ├── orchestrator/            Stage runner, sub-agent dispatch, Flash + gh wrappers
│   ├── pdd_workflows/           VENDORED PDD workflows — do not edit directly
│   ├── server/                  anvil serve (LangServe wrapper + web UI)
│   └── templates/               Starter LangGraph project templates
├── pdd/                         Anvil itself is a PDD project (this directory)
├── tests/                       pytest unit tests
└── examples/                    Reference projects built with Anvil
```

## Naming

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions, vars: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Prompts: `<name>.vMAJOR.MINOR.PATCH.md` — version bump on any content change
- Sub-agents: `NodeForge`, `EvalSmith`, `DocScribe`, `MergeBot` — fixed names, never invent new ones

## Type hints

- Mandatory on all public functions
- `mypy --strict` clean; no `Any` without a `# type: ignore[...]` reason comment
- Use `from __future__ import annotations` at the top of every module so forward references work

## Async

- All Flash calls are async (`client.aio.models.generate_content`)
- All orchestrator stage functions are async
- CLI entry points wrap async work with `asyncio.run`
- Use `asyncio.gather` for parallel sub-agent dispatch

## Error handling

- Raise typed exceptions, never bare `Exception`
- Define module-local exception types: `class NodeForgeError(Exception): ...`
- Never swallow with `except: pass`; if you catch, you log and re-raise or transform
- Wrap external calls (Gemini, gh, file I/O) in `tenacity.retry` with exponential backoff, max 3 attempts

## Logging

- `logger = logging.getLogger(__name__)` at module top
- No `print()` in library code; `rich.console.Console` is fine in `commands/` for user-facing output
- Log entry, exit, and any retry attempt on Flash calls
- INFO level for stage transitions, DEBUG for Flash request/response, ERROR for failures

## LLM-specific

- Every Flash call must specify: model, temperature, response schema
- Code-generating sub-agents (NodeForge, EvalSmith): temperature `0.2`
- Prose-generating sub-agents (DocScribe, MergeBot): temperature `0.4`
- Never construct prompts via string concatenation in code; prompts live in `pdd/prompts/`
- Load prompt files at runtime via `importlib.resources` so they ship with the package

## Prompt mirroring (pdd/ ↔ anvil/prompts/)

The canonical sub-agent prompts live at `pdd/prompts/features/sub-agents/`. They are mirrored into `anvil/prompts/sub-agents/` for runtime loading via `importlib.resources` (the package data ships in the wheel; the `pdd/` tree does not).

When editing a prompt:
1. Edit the file in `pdd/prompts/features/sub-agents/` (the source of truth).
2. Copy the change to `anvil/prompts/sub-agents/` with the same filename.
3. Bump the version suffix on both files if the change is non-trivial (e.g., `v1.0.0` → `v1.1.0`).

Drift detection is a post-hackathon item. For now, both directories are checked into git, so reviewers can see any drift in PR diffs.

## Comments and docstrings

- Default to no comments; the code should be self-documenting via names
- Only add a comment when the *why* is non-obvious (hidden constraint, workaround for a known bug)
- Module-level docstrings: one line describing purpose, optionally a second paragraph for non-obvious context
- Function docstrings: one line; signature + name should carry most of the meaning
- No multi-paragraph docstrings, no example blocks in docstrings (put examples in `examples/`)

## Testing

- Unit tests live in `tests/`, mirror the package layout
- Async tests via `pytest-asyncio` with `asyncio_mode = "auto"`
- Mock the Gemini SDK at the boundary, not deeper — patch `client.aio.models.generate_content`
- Never mock LangGraph internals; treat it as a stable dependency
- Evals are NOT in `tests/` — they live in user-project `evals/` directories and use LLM-as-judge

## Anti-patterns (auto-reject in PR review)

- Bare `except:` clauses
- `print()` outside of `commands/` and `cli.py`
- Mutating state in place inside a LangGraph node
- Hardcoded API keys, URLs, model names
- Prompts as multi-line f-strings inside Python code
- Multi-paragraph docstrings on simple functions
- Re-implementing what `tenacity`, `typer`, or `langserve` already does
- Backwards-compat shims (renamed `_old_name = new_name`) — just change callers
