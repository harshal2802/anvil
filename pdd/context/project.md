# Project: Anvil

## What we're building

A Git-native, eval-driven IDE for agent graphs. Anvil turns one English sentence into a complete LangGraph project — scaffolded repo, PDD context files, phased implementation plan, GitHub issues, and pull requests shipping code + evals + ADRs together. It runs on Gemini 3.5 Flash and uses parallel sub-agents for the inner execution loop.

## Who it's for

- AI engineers past the prototyping phase, shipping agentic systems to production
- Platform teams standardizing how agents are built across product teams (the **wedge audience** — they need governance, not a prettier canvas)
- Technical PMs and solutions engineers who can describe a workflow but not write LangGraph by hand

## Tech stack

- **Language:** Python 3.11+
- **CLI:** Typer (built on Click) + Rich for formatting
- **LLM:** Google Gemini 3.5 Flash via `google-genai` SDK (async client)
- **Agent runtime:** LangGraph 0.2+
- **Serving:** LangServe + FastAPI + uvicorn
- **Web UI:** vanilla HTML + htmx + SSE (no build step, hackathon-appropriate)
- **Process discipline:** PDD (vendored at pinned SHA — see [NOTICE.md](../../NOTICE.md))
- **VCS & CI:** git + GitHub via `gh` CLI
- **Testing:** pytest + pytest-asyncio + LLM-as-judge for eval suites

## What good output looks like

- Every generated artifact is reviewable by a human in under two minutes
- Generated LangGraph code runs without Anvil installed (zero runtime lock-in)
- Each phase ships as a single PR with code + evals + ADR together
- All prompts are versioned PDD artifacts (this directory dogfoods that)
- The orchestrator is auditable — every Flash call traces to a vendored workflow file + a versioned prompt file

## Constraints (what the AI should never do or suggest)

- Never hardcode model names, API keys, URLs, or magic numbers — pass via state or env vars
- Never use bare `except:` or swallow exceptions silently — raise typed errors
- Never mutate state in place inside a LangGraph node — return a delta dict
- Never use `print()` in library code — use `logging.getLogger(__name__)`
- Never bolt on backwards-compat shims during the hackathon — if an interface changes, just change it and update callers
- Never write multi-paragraph docstrings or multi-line comment blocks — one short line max, let names carry the meaning
- Never use `cat`/`head`/`tail` in tool output when a dedicated tool exists

## Current state

Hackathon scaffold (2026-05-23). Status:

- README + four-mode pitch locked
- PDD workflows vendored at SHA `f83deb4…`
- Typer CLI dispatches to six subcommand modules
- Anvil's own `pdd/` directory (this folder) — established and maintained
- Dev environment pinned to Homebrew `python@3.13` with `--copies` venv; `make {dev,lint,test}` covers the loop (see [decisions.md](decisions.md))
- **`anvil run --phase 1` shipped** — orchestrator core wires NodeForge → EvalSmith ∥ DocScribe → MergeBot
- **`anvil init` greenfield shipped** — ProjectScribe → ConventionsScribe ∥ PlanScribe produces a Flash-tailored project
- Remaining subcommands (`plan`, `edit`, `serve`, `status`) are stubs; per-subcommand PLANs in flight under [pdd/prompts/features/](../prompts/features/)

The seven sub-agent prompts under [`pdd/prompts/features/sub-agents/`](../prompts/features/sub-agents/) are the source of truth — four for `anvil run` per-phase work (NodeForge, EvalSmith, DocScribe, MergeBot) and three for `anvil init` greenfield (ProjectScribe, ConventionsScribe, PlanScribe).

---

## CLI / Developer Tools specifics

(From `references/cli-devtools.md` in the upstream PDD skill — applied here.)

- Subcommands: `init`, `plan`, `run`, `edit`, `serve`, `status`
- Entry point: `anvil = anvil.cli:app` in `pyproject.toml`
- Argument parsing: Typer; never raw `argparse`
- User-facing errors: Rich-formatted, never raw tracebacks
- Install command: `pip install anvil-cli` (PyPI name; `anvil` is taken by Anvil Works)

## AI / Agent project specifics

(From `references/data-ml.md` in the upstream PDD skill — applied here, with agent-graph extensions.)

- Default model: `gemini-3.5-flash`
- All Flash calls use structured output (`response_mime_type="application/json"` + `response_schema`)
- Sub-agents run in parallel via `asyncio.gather` where dependencies allow
- Prompts are markdown files in this `pdd/` tree, versioned by filename suffix (`*.vMAJOR.MINOR.PATCH.md`)
- Evals use LLM-as-judge (Gemini 2.5 Pro as judge) against explicit rubrics — never `assertEqual` for stochastic outputs
- Agent state is a `TypedDict`; nodes are pure async functions returning delta dicts
