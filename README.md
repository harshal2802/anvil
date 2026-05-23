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
$ anvil init --existing

# 3. Conversational extension — change anything by describing the change
$ anvil edit "Add retry-on-429 to the email_send node:
              3 attempts, exponential backoff, jitter"

# 4. Ship it — host the graph as an API with a live chat UI
$ anvil serve --web
> Anvil serving graph on http://localhost:8000
> Live graph visualization at http://localhost:8000/inspect
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
              ┌────────────────────────────────────┐
              │ Per-phase execution loop           │
              │                                    │
              │  PDD: prompts → versioned .md      │
              │           │                        │
              │           ▼                        │
              │  Four Flash sub-agents (parallel): │
              │   ┌──────────┬──────────┐          │
              │   │NodeForge │EvalSmith │          │
              │   └──────────┴──────────┘          │
              │   ┌──────────┬──────────┐          │
              │   │DocScribe │MergeBot  │          │
              │   └──────────┴──────────┘          │
              │           │                        │
              │           ▼                        │
              │  PDD: review → PDD: eval → PR      │
              └────────────────────────────────────┘
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

Each runs in parallel via `asyncio.gather`. Total wall time ≈ time of a single Flash call.

---

## Quick start *(work in progress — hackathon scaffold)*

```bash
# 1. Install (PyPI package name TBD — `anvil` is taken by Anvil Works)
pip install anvil-cli

# 2. Set up auth
gh auth login                    # GitHub
export GOOGLE_API_KEY=...        # Gemini 3.5 Flash

# 3. Greenfield: build a project from one sentence
anvil init "Describe what you want the agent to do"

# 4. Or, brownfield: bring PDD to an existing LangGraph project
cd your-existing-project
anvil init --existing

# 5. Extend the project conversationally
anvil edit "Describe the change you want to make"

# 6. Host it as an API with a live graph view
anvil serve --web
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
- [ ] CLI: `anvil init` (greenfield + brownfield), `anvil edit`, `anvil serve`, `anvil status`
- [ ] Stage orchestrator that executes PDD workflows via Gemini Flash
- [ ] Four parallel Flash sub-agents (NodeForge, EvalSmith, DocScribe, MergeBot)
- [ ] GitHub integration via `gh` CLI — issues per phase, PR per change
- [ ] LangServe wrapper for `anvil serve`
- [ ] Web UI with live graph visualization during execution
- [ ] One reference workflow built live during the demo

**Post-hackathon:**
- VS Code extension
- Multi-graph projects (sub-graphs, hierarchical agents)
- Drift detection between vendored PDD and upstream
- Submit `references/agent-graph.md` upstream to `pdd-skill`

Checkboxes update as the build progresses through the hackathon window.

---

## What was built during the hackathon

Per the [Google I/O 2026 hackathon rules](https://cerebralvalley.ai/e/google-io-hackathon), this section makes the contribution boundary explicit. See [NOTICE.md](NOTICE.md) for the full version.

**Built during the hackathon (this repo, all new code):**
- The Anvil CLI (`anvil/cli.py`, `anvil/commands/`)
- The stage orchestrator and the four Flash sub-agent prompts (`anvil/orchestrator/`)
- The visual graph renderer + live execution view (`anvil/server/web/`)
- The GitHub and LangServe integration layers
- All example projects in `examples/`

**Used as dependencies (not submitted as hackathon work):**
- **[PDD (Prompt Driven Development)](https://github.com/harshal2802/pdd-skill)** — prior open-source work by the same author. Vendored at a pinned SHA; see [NOTICE.md](NOTICE.md).
- **[LangGraph](https://github.com/langchain-ai/langgraph)** — the agent runtime Anvil generates code for.
- **Gemini 3.5 Flash** — the model powering every sub-agent in the orchestrator.
- **LangServe, FastAPI, Typer, react-flow** — standard libraries used as intended.

No code or assets were copied from other projects. All Anvil source is original work created during the hackathon window.

---

## Built by

[Harshal Chourasiya](https://github.com/harshal2802) — at the Google I/O 2026 hackathon hosted by Cerebral Valley.

## License

[MIT](LICENSE)
