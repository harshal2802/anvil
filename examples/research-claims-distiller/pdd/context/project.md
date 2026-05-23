# Project: Research Claims Distiller

## What we're building
An automated, stateful LangGraph agent that ingests a list of target URLs, concurrently fetches and parses their content, extracts verifiable claims, and synthesizes them into a structured, one-page executive brief. The agent uses a map-reduce architecture to process sources in parallel before compiling the final consolidated report with inline citations.

## Who it's for
- **Market Researchers** who need to quickly synthesize competitor press releases and product announcements without manual copy-pasting.
- **Policy Analysts** tracking regulatory updates and public statements across multiple agency portals.
- **Academic Assistants** compiling preliminary literature reviews from a curated list of open-access web sources.

## Tech stack
- **Python 3.11+**
- **LangGraph 0.2+** (for stateful orchestration of fetching, extraction, and synthesis nodes)
- **Gemini Flash** (via `google-genai` for extraction and summarization)
- **httpx** (for non-blocking, asynchronous HTTP requests)
- **beautifulsoup4** (for robust HTML parsing and boilerplate removal)
- **pydantic** (for strict validation of extracted claims and citation schemas)

## What good output looks like
- A single-page Markdown document (under 600 words) containing a high-level summary, a categorized list of key claims, and a bibliography.
- Every extracted claim must be mapped to a numbered inline citation (e.g., `[1]`) that corresponds directly to the source URL.
- A "Sources Cited" section at the bottom of the brief containing the page title, domain, and exact URL for each reference.
- A dedicated "Failed Sources" section listing any URLs that returned 4xx/5xx errors or timed out, ensuring the user has full visibility into missing data.

## Constraints
- Never synthesize or extrapolate claims that cannot be directly mapped back to the raw text retrieved from the source URLs.
- Never perform synchronous HTTP requests; all page fetches must be executed asynchronously using `httpx.AsyncClient` with a strict 10-second timeout per URL.
- Never use raw regular expressions to parse HTML bodies; always use `beautifulsoup4` to isolate the primary text content.
- Never output raw JSON or unformatted text to the final user; the output must always be valid, readable Markdown.

## Current state
Greenfield. Scaffolded via anvil init on 2026-05-23. No nodes implemented yet.