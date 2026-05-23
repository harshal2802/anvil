# Anvil

**A Git-native, eval-driven IDE for agent graphs.**

Anvil turns one English sentence into a production-ready LangGraph node — with code, evals, an architecture decision record, and a real GitHub pull request — in the time it takes one model to think. Four Gemini 3.5 Flash sub-agents run in parallel; one PR comes off the anvil.

> Built at the **Google I/O 2026 hackathon**. See [What was built during the hackathon](#what-was-built-during-the-hackathon) for the contribution boundary.

---

## The 30-second demo

```bash
$ anvil add-node "Fetch a URL and return a 3-sentence summary using the LLM in state"

  Forging node...
  ├─ NodeForge   ✓ summarize_url.py            (1.4s)
  ├─ EvalSmith   ✓ evals/test_summarize_url.py (1.6s)
  ├─ DocScribe   ✓ docs/adr/007-summarize.md   (1.5s)
  └─ MergeBot    ✓ PR body + title             (1.3s)

  Branch:  anvil/add-summarize-url
  Commit:  feat: add summarize_url node
  PR:      https://github.com/you/your-graph/pull/42  ← opened
```

*[demo.gif placeholder — recorded during the hackathon]*

Every file in that PR is reviewable, version-controlled, and runnable without Anvil installed. The graph is the source artifact; the discipline is the product.

---

## What Anvil produces per change

A single `anvil add-node` invocation creates four artifacts that ship together:

```
your-langgraph-project/
├── nodes/
│   └── summarize_url.py              ← NodeForge
├── evals/
│   ├── test_summarize_url.py         ← EvalSmith (pytest + LLM-as-judge)
│   └── golden/summarize_url.jsonl    ← 7 cases: 3 happy / 2 edge / 2 failure
└── docs/adr/
    └── 007-summarize.md              ← DocScribe (Michael Nygard format)
```

Plus a GitHub PR with a real description, file-level change summary, and reviewer checklist — drafted by **MergeBot**.

---

## Why Anvil exists

Visual agent builders (LangFlow, Flowise, and others) optimized for *prototyping*. They are excellent at that job. The moment a workflow needs to be reviewed, versioned, evaluated, and shipped to production, the discipline that real software requires has to be added back by hand: tests, ADRs, PR hygiene, change provenance.

Platform teams standardizing how agents are built across an org feel this acutely. They don't need a prettier canvas; they need a workflow that produces *reviewable, reproducible* agent code.

Anvil's wedge: **the visual graph is a view of code, not the source of truth.** The code is LangGraph Python. It runs anywhere — production included, with Anvil uninstalled.

---

## How it works

```
  User intent (one sentence)
            │
            ▼
   ┌──────────────────┐
   │ Context Builder  │   reads current graph + repo conventions
   └────────┬─────────┘
            │
            ▼
  ┌─────────────────────────────────────────────────────┐
  │       Gemini 3.5 Flash × 4 — parallel sub-agents    │
  ├──────────────┬──────────────┬───────────┬───────────┤
  │  NodeForge   │  EvalSmith   │ DocScribe │ MergeBot  │
  │  → code      │  → evals     │ → ADR     │ → PR      │
  └──────────────┴──────────────┴───────────┴───────────┘
            │
            ▼
     git commit + gh pr create
```

Why Flash specifically: this whole pipeline only works if four LLM calls finish in roughly the time of one. Flash's latency and cost profile is what makes the parallel fan-out demo-able instead of a 30-second loading spinner.

---

## Quick start *(work in progress — hackathon scaffold)*

```bash
# 1. Install
pip install anvil-cli            # package name TBD; PyPI namespace check in progress

# 2. Authenticate
anvil auth login                 # uses gh CLI under the hood
export GOOGLE_API_KEY=...        # Gemini 3.5 Flash

# 3. Initialize Anvil in an existing LangGraph repo
cd your-langgraph-project
anvil init

# 4. Forge your first node
anvil add-node "Describe what you want the node to do, in plain English"
```

---

## How Anvil compares

|                          | LangFlow / Flowise         | Hand-written LangGraph     | **Anvil**                  |
|--------------------------|----------------------------|----------------------------|----------------------------|
| Source of truth          | Visual canvas              | Code                       | **Code (graph is a view)** |
| Output runs without tool | No (custom runtime)        | Yes                        | **Yes (raw LangGraph)**    |
| Per-change evals         | Manual                     | Manual                     | **Generated**              |
| Decision provenance      | None                       | Manual ADRs                | **Generated**              |
| PR hygiene               | N/A                        | Manual                     | **Generated**              |
| Best for                 | Prototyping                | Senior engineers           | **Production agent teams** |

This is not a knock on LangFlow — it's an excellent prototyping tool. Anvil targets the next stage: the team that has outgrown prototyping and needs to ship.

---

## Roadmap

**Shipped during the hackathon (May 2026):**
- [ ] CLI: `anvil add-node` end-to-end
- [ ] Four parallel Flash sub-agents (NodeForge, EvalSmith, DocScribe, MergeBot)
- [ ] Real PR creation via `gh` CLI
- [ ] Visual graph rendering (react-flow)
- [ ] Live "sub-agents working" UI panel
- [ ] One reference workflow recorded end-to-end

**Post-hackathon:**
- Conversational node editing ("make node 3 retry on 429")
- Bidirectional code ↔ graph sync (edit graph → code updates, edit code → graph updates)
- Eval runner CI integration
- Multi-node workflows in a single intent ("build a research → summarize → email pipeline")
- VS Code extension

Checkboxes update as the build progresses through the hackathon.

---

## What was built during the hackathon

Per the [Google I/O 2026 hackathon rules](https://cerebralvalley.ai/e/google-io-hackathon), this section makes the contribution boundary explicit.

**Built during the hackathon (this repo, all new code):**
- The Anvil CLI, orchestrator, and four Flash sub-agent prompts
- The visual graph renderer + sub-agent panel
- The GitHub integration layer

**Used as dependencies (not submitted as hackathon work):**
- **[LangGraph](https://github.com/langchain-ai/langgraph)** — the runtime Anvil generates code for
- **Gemini 3.5 Flash** — the model powering all four sub-agents
- **[PDD (Prompt Driven Development)](https://github.com/harshal2802/pdd-skill)** — a prior open-source methodology by the same author. Anvil uses PDD as a *process discipline* (prompts are versioned engineering artifacts in `prompts/`); the PDD repo itself is not part of this submission.
- **react-flow, FastAPI, Next.js** — standard libraries used as intended

No code or assets were copied from other projects. All Anvil source is original work created during the hackathon window.

---

## Built by

[Harshal Chourasiya](https://github.com/harshal2802) — at the Google I/O 2026 hackathon hosted by Cerebral Valley.

## License

[MIT](LICENSE)
