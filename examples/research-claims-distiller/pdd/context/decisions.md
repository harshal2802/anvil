## Decision: Scaffolded via anvil init on 2026-05-23

**Date:** 2026-05-23

**What was decided:** We decided to build the Research Claims Distiller using Python 3.11+, LangGraph 0.2+, Gemini Flash via the `google-genai` SDK, `httpx`, `beautifulsoup4`, and `pydantic` to orchestrate a stateful, parallel map-reduce pipeline for web scraping, claim extraction, and synthesis.

**Why:** This stack was chosen because LangGraph natively supports stateful map-reduce workflows, Gemini Flash provides cost-effective and fast extraction, and `httpx` enables non-blocking concurrent fetches.

**Don't suggest:** Do not suggest rewriting the orchestration layer in TypeScript or replacing LangGraph with a custom asyncio queue implementation.