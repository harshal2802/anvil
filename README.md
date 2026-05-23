# Anvil

**A Git-native, eval-driven IDE for agent graphs.**

One CLI. One sentence. A complete LangGraph project with engineering discipline at every step.

> Built at the **Google I/O 2026 hackathon**. See [What was built during the hackathon](#what-was-built-during-the-hackathon) for the contribution boundary.

---

## Four modes, one tool

```bash
# 1. Greenfield — scaffold a new project from a description
$ anvil init "Build a customer support agent: triage email, draft reply,
              escalate low-confidence cases to humans"

# 2. Brownfield — bring PDD discipline to an existing LangGraph repo
$ cd existing-agent-project
$ anvil init --existing                       # ← post-hackathon

# 3. Conversational extension — change anything by describing the change
$ anvil edit "Add retry-on-429 to the email_send node:
              3 attempts, exponential backoff, jitter"

# 4. Ship it — host the graph as an API with a live chat UI
$ anvil serve --web
> Anvil serving graph on http://127.0.0.1:8000
> Live graph visualization at http://127.0.0.1:8000/
```

Plus two supporting commands:

```bash
$ anvil plan   "Add a refund-eligibility node"  # PlanScribe + gh issues per phase
$ anvil run    --phase 1                         # NodeForge → EvalSmith ∥ DocScribe → MergeBot
$ anvil status                                   # read-only project dashboard
```

Each mode produces real artifacts — code, evals, decision records, pull requests — committed to a real git repo, openable in a real GitHub PR. The graph is the source artifact; the engineering discipline around it is the product.

---

## What Anvil produces

Every `anvil` invocation generates four artifacts that ship together as a PR:

```
your-agent-project/
├── pdd/                              ← the PDD layer (process discipline)
│   ├── context/
│   │   ├── project.md                ← what, who, stack, constraints
│   │   ├── conventions.md            ← style, patterns, anti-patterns
│   │   └── decisions.md              ← architectural decisions log
│   ├── prompts/
│   │   └── features/<area>/
│   │       ├── PLAN-<feature>.md     ← phased implementation plan
│   │       └── <feature>-NN-<phase>.md  ← versioned prompt artifacts
│   └── evals/
│       ├── baselines/                ← known-good outputs
│       └── scripts/                  ← scripted validation
├── src/
│   └── nodes/                        ← generated LangGraph nodes (Python)
├── evals/
│   ├── test_<node>.py                ← pytest + LLM-as-judge
│   └── golden/                       ← 7-case datasets (3 happy / 2 edge / 2 fail)
├── docs/
│   └── adr/                          ← Architecture Decision Records
└── graph.py                          ← the assembled LangGraph
```

Plus a real GitHub PR for every change — title, body, file-level summary, risk section, reviewer checklist — drafted by an agent and openable via `gh`.

---

## How it works

Anvil runs **Gemini 3.5 Flash sub-agents** at each stage of the PDD lifecycle. Each stage consumes the previous stage's output as structured context.

```
        ┌─────────────────────────────────────────────┐
        │            anvil init "<description>"       │
        └─────────────────────┬───────────────────────┘
                              │
            ┌─────────────────┴──────────────────┐
            ▼ (greenfield)                       ▼ (brownfield, --existing)
    ┌──────────────────┐                  ┌──────────────────────┐
    │ PDD: scaffold    │                  │ PDD: init             │
    │ Flash creates    │                  │ Detect stack          │
    │ new repo + pdd/  │                  │ Confirm w/ user       │
    │                  │                  │ Add pdd/ to existing  │
    └────────┬─────────┘                  └──────────┬────────────┘
             └─────────────────┬──────────────────────┘
                               ▼
                  ┌──────────────────────────┐
                  │ PDD: context             │
                  │ Flash writes:            │
                  │  - project.md            │
                  │  - conventions.md        │
                  │  - decisions.md          │
                  └────────────┬─────────────┘
                               ▼
                  ┌──────────────────────────┐
                  │ PDD: plan                │
                  │ Flash → PLAN.md          │
                  │ gh CLI → GitHub issues   │
                  │ (one per phase)          │
                  └────────────┬─────────────┘
                               ▼
              ┌─────────────────────────────────────────────┐
              │ Per-phase execution loop (`anvil run`)      │
              │                                             │
              │  PDD: prompts → versioned .md               │
              │           │                                 │
              │           ▼                                 │
              │  NodeForge                  (step 1)        │
              │           │                                 │
              │           ▼                                 │
              │  EvalSmith  ∥  DocScribe    (step 2 ‖ via   │
              │           │                  asyncio.gather)│
              │           ▼                                 │
              │  MergeBot                   (step 3 —       │
              │           │                  needs eval +   │
              │           ▼                  ADR outputs)   │
              │  PR draft → review → ship                   │
              └─────────────────────────────────────────────┘
```

**Why Gemini Flash specifically:** the inner loop runs four LLM calls in parallel. The entire pipeline only feels fast — and demo-able in real time — because Flash's latency and cost profile permits a fan-out shape that would be prohibitive on slower or more expensive models. The hackathon prompt asks for something that's only possible with Flash; this is it.

---

## The four sub-agents

These are the inner loop. Every phase of every feature passes through these four in parallel:

| Sub-agent     | Output                                                      |
|---------------|-------------------------------------------------------------|
| **NodeForge** | A production-ready LangGraph node (typed, logged, retried) |
| **EvalSmith** | Eval suite — golden dataset + pytest + LLM-as-judge runner |
| **DocScribe** | An Architecture Decision Record in Michael Nygard format  |
| **MergeBot**  | PR title, body, reviewer checklist, and labels             |

Three honest steps with two-way parallelism in step 2 (EvalSmith ∥ DocScribe via `asyncio.gather`). MergeBot sequences after because its PR body references the eval filename and ADR title — pretending it can run in parallel would mean either a useless PR body or post-editing it after the fact. Total wall time ≈ time of three Flash calls. See [decisions.md](pdd/context/decisions.md) "Three-step sub-agent execution shape".

---

## Quick start

```bash
# 1. Install — PyPI publish is post-hackathon; for now, from source:
git clone https://github.com/harshal2802/anvil && cd anvil
make dev                         # creates .venv with `--copies`, installs editable

# 2. Set up auth
gh auth login                    # GitHub (for `anvil plan` issue creation)
export GOOGLE_API_KEY=...        # Gemini 3.5 Flash

# 3. Greenfield: build a project from one sentence
anvil init "Describe what you want the agent to do"
cd <slug>                        # ProjectScribe-chosen directory name

# 4. Ship phase 1 — NodeForge → EvalSmith ∥ DocScribe → MergeBot
anvil run --phase 1

# 5. Extend conversationally
anvil edit "Describe the change you want to make"

# 6. Open one GitHub issue per phase
anvil plan "Add a refund-eligibility node"

# 7. Read-only dashboard
anvil status

# 8. Host as an API with a live graph view
anvil serve --web
> http://127.0.0.1:8000/

# (post-hackathon) anvil init --existing — brownfield retrofit
```

---

## How Anvil compares

|                          | LangFlow / Flowise         | Hand-written LangGraph     | **Anvil**                       |
|--------------------------|----------------------------|----------------------------|---------------------------------|
| Source of truth          | Visual canvas              | Code                       | **Code (graph is a view)**      |
| Greenfield project setup | Manual                     | Manual                     | **`anvil init`**                |
| Brownfield retrofit      | N/A                        | Manual                     | **`anvil init --existing`**     |
| Per-change evals         | Manual                     | Manual                     | **Generated**                   |
| Decision provenance      | None                       | Manual ADRs                | **Generated**                   |
| PR hygiene               | N/A                        | Manual                     | **Generated**                   |
| Conversational edits     | Drag & drop                | Manual                     | **`anvil edit`**                |
| Deployment               | Tied to runtime            | Manual                     | **`anvil serve`**               |
| Output portability       | Locked to runtime          | Portable                   | **Portable (raw LangGraph)**    |

This is not a knock on LangFlow — it's a great prototyping tool. Anvil targets the next stage: teams that have outgrown prototyping and need to ship.

---

## PDD: the process backbone

Anvil's process discipline comes from **[PDD (Prompt Driven Development)](https://github.com/harshal2802/pdd-skill)** — an open-source methodology that treats prompts as versioned engineering artifacts: specs, plans, evals, decisions, and reviews, all stored in the repo as durable markdown.

PDD's workflow files (`scaffold`, `init`, `context`, `plan`, `prompts`, `eval`, `review`) are vendored at a pinned commit SHA under [`anvil/pdd_workflows/`](anvil/pdd_workflows/). Anvil's stage orchestrator reads these files and feeds them as system context to Gemini Flash, so every Anvil run faithfully executes the published PDD methodology. See [NOTICE.md](NOTICE.md) for the full vendoring policy and attribution.

**Dogfooding:** Anvil itself is a PDD project. Anvil's four sub-agent prompts live in versioned files under `pdd/prompts/features/sub-agents/`. The same discipline Anvil applies to user projects is applied to Anvil's own development. Look in `pdd/` to see PDD running on the tool that runs PDD.

---

## Roadmap

**Shipped during the hackathon (May 2026):**
- [x] CLI surface: `anvil init`, `anvil plan`, `anvil run`, `anvil edit`, `anvil serve`, `anvil status` (6 subcommands)
- [x] Stage orchestrator running PDD workflows via Gemini Flash (`anvil run --phase 1`)
- [x] Seven Flash sub-agents: NodeForge, EvalSmith, DocScribe, MergeBot (per-phase loop) + ProjectScribe, ConventionsScribe, PlanScribe (`anvil init` greenfield)
- [x] GitHub integration via `gh` CLI — `anvil plan` opens one issue per phase, MergeBot drafts the PR body
- [x] LangServe wrapper for `anvil serve` (bare mode: `/invoke`, `/playground`, `/stream`)
- [x] Web UI with live graph visualization during execution (`anvil serve --web` — vanilla htmx + SSE, no build step)
- [x] `anvil edit` conversational extension (composition over orchestration — reuses `forge_phase` + a scoped `PlanScribe`)
- [x] Read-only project dashboard (`anvil status` — phases, evals, prompt versions)
- [x] PDD dogfooded throughout — every Anvil sub-agent prompt lives in versioned `pdd/prompts/features/sub-agents/`

**Deferred to post-hackathon:**
- `anvil init --existing` (brownfield retrofit)
- `gh pr create` wiring inside `anvil run` / `anvil edit` (MergeBot drafts the PR; opening it is currently manual)
- Flash-based target-node detection for `anvil edit` (v1 is deterministic token-overlap; the Flash escalation point is marked with a TODO)
- LLM-as-judge quality evals over generated `project.md` and node code
- VS Code extension
- Multi-graph projects (sub-graphs, hierarchical agents)
- Drift detection between vendored PDD and upstream
- Submit `references/agent-graph.md` upstream to `pdd-skill`

Checkboxes update as the build progresses through the hackathon window.

---

## What was built during the hackathon

Per the [Google I/O 2026 hackathon rules](https://cerebralvalley.ai/e/google-io-hackathon), this section makes the contribution boundary explicit. See [NOTICE.md](NOTICE.md) for the full version.

**Built during the hackathon (this repo, all new code):**
- The Anvil CLI (`anvil/cli.py`, `anvil/commands/`) — six subcommands wired end-to-end
- The stage orchestrator (`anvil/orchestrator/`) and the seven Flash sub-agent prompts under `anvil/prompts/sub-agents/` (mirrored from canonical `pdd/prompts/features/sub-agents/`)
- The LangServe wrapper + vanilla HTML / htmx / SSE live graph view (`anvil/server/`)
- The GitHub integration layer (`gh` CLI driven from `anvil/commands/plan.py`)

**Used as dependencies (not submitted as hackathon work):**
- **[PDD (Prompt Driven Development)](https://github.com/harshal2802/pdd-skill)** — prior open-source work by the same author. Vendored at a pinned SHA; see [NOTICE.md](NOTICE.md).
- **[LangGraph](https://github.com/langchain-ai/langgraph)** — the agent runtime Anvil generates code for.
- **Gemini 3.5 Flash** — the model powering every sub-agent in the orchestrator.
- **LangServe, FastAPI, Typer, Rich, htmx (CDN), sse-starlette** — standard libraries used as intended. No JS framework, no build step.

No code or assets were copied from other projects. All Anvil source is original work created during the hackathon window.

---

## Built by

[Harshal Chourasiya](https://github.com/harshal2802) — at the Google I/O 2026 hackathon hosted by Cerebral Valley.

## License

[MIT](LICENSE)
