# Decisions

Architectural choices that should not be relitigated without explicit reason. Each entry: what was decided, why, and what alternatives to avoid suggesting.

---

## Decision: Vendor PDD workflows at a pinned SHA

**Date:** 2026-05-23
**What was decided:** Copy the PDD workflow markdown files from `harshal2802/pdd-skill` into `anvil/pdd_workflows/` at a pinned commit SHA, with a header banner marking provenance.
**Why:** PDD is a Claude-Code-skill (a directory of markdown), not a Python package — nothing to `pip install`. Vendoring gives zero install friction, reproducible behavior across Anvil versions, and a clean attribution boundary.
**Don't suggest:** Git submodule (painful for users), runtime `git clone` of pdd-skill (network dependency, non-reproducible), or rewriting the PDD workflows inside Anvil (drift from upstream).

---

## Decision: Each sub-agent is its own Flash call

**Date:** 2026-05-23
**What was decided:** NodeForge, EvalSmith, DocScribe, and MergeBot are four independent Gemini Flash calls — not one combined call producing all four artifacts.
**Why:** Lets us tune temperature per artifact type (code at 0.2, prose at 0.4), gives clean parallelism, and isolates failures (a bad ADR doesn't poison the code). Each sub-agent gets its own focused system prompt, which empirically yields better outputs than a single mega-prompt.
**Don't suggest:** Combining sub-agents into a single Flash call, or serializing them when they could parallelize.

---

## Decision: NodeForge runs first; other three fan out in parallel

**Date:** 2026-05-23
**What was decided:** Sequence is `NodeForge` → `asyncio.gather(EvalSmith, DocScribe, MergeBot)`. EvalSmith and DocScribe need NodeForge's output to produce meaningful artifacts.
**Why:** True four-way parallelism is faster but produces lower-quality EvalSmith/DocScribe outputs (they'd be working from intent alone, not code). The staged shape is honest about the dependency while keeping demo latency low (~2 Flash calls in wall time, not 4).
**Don't suggest:** True four-way parallelism for production. (For demo theatre, the UI can animate all four panels from t=0 — that's a presentation choice, not a runtime change.)

---

## Decision: Structured JSON output via response_schema, not free-text parsing

**Date:** 2026-05-23
**What was decided:** All Flash calls use `response_mime_type="application/json"` with an explicit `response_schema`.
**Why:** Free-text JSON parsing fails on edge cases (Flash adds preamble, trailing commas, code-fences). Structured-output mode is enforced server-side and is reliable.
**Don't suggest:** `json.loads` on raw Flash text output, regex-extracting JSON blocks, or asking Flash to "respond with only JSON."

---

## Decision: PR-per-phase, not PR-per-feature

**Date:** 2026-05-23
**What was decided:** Each phase in a PLAN.md ships as its own PR. A multi-phase feature produces multiple PRs that merge in sequence.
**Why:** Matches PDD's `prompts.md` guidance (one prompt → one reviewable artifact). Keeps individual PRs small enough for human reviewers. Failed evals on one phase don't block downstream phases from being designed.
**Don't suggest:** Bundling phases into a single PR "for convenience" — it defeats the reviewability goal that is Anvil's entire wedge.

---

## Decision: `anvil-cli` PyPI package, `anvil` CLI command

**Date:** 2026-05-23
**What was decided:** PyPI package name is `anvil-cli`. The installed CLI binary is `anvil`. Python imports are `from anvil import ...`.
**Why:** `anvil` on PyPI is taken by Anvil Works. The CLI surface is what users interact with daily; the install command is one-time. Optimizing the daily surface is correct.
**Don't suggest:** Renaming the CLI to `anvil-cli` to match the package, or picking a different brand name to satisfy PyPI.

---

## Decision: Web UI is vanilla HTML + htmx + SSE, no build step

**Date:** 2026-05-23
**What was decided:** `anvil serve --web` ships a single static HTML page using htmx for interactivity and Server-Sent Events for streaming Flash responses.
**Why:** Hackathon scope. A Next.js/React setup adds 4+ hours of build configuration and deploy complexity for no demo benefit. htmx + SSE is one HTML file that any browser can load directly.
**Don't suggest:** Adding a JavaScript build step, a frontend framework, or a separate UI repo — until post-hackathon.

---

## Decision: Conversational `anvil edit` is composition, not new orchestration

**Date:** 2026-05-23
**What was decided:** `anvil edit "<change>"` internally runs `plan` (single-phase scope) + `run` against the targeted phase, with an extra detection step to identify which node(s) the change touches.
**Why:** Keeps the orchestrator simple — one execution path for all multi-Flash work. Tier 3 collapses to ~1 day of work because most of the machinery exists.
**Don't suggest:** A separate "edit" orchestrator with its own sub-agents — it would diverge from `run` and double the maintenance surface.
