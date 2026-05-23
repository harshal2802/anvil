## ADR-001: Add summarize_url node for robust webpage fetching and summarization
**Status:** Proposed
**Date:** 2026-05-23

## Context
The existing graph only contains the `load_inputs` node, which reads the target URL but lacks any capability to retrieve or process remote content. To generate insights from external web pages, the system needs a reliable way to fetch HTML, parse text, and handle transient network failures. Additionally, we must handle extremely long pages and manage external LLM dependencies without hardcoding specific model clients.

## Decision
We will add the `summarize_url` node to fetch raw HTML using `httpx` with exponential backoff retries via `tenacity`. This node will extract and truncate the main text using `BeautifulSoup` and generate a three-sentence summary using an LLM client passed dynamically through the `GraphState`.

## Consequences
* Improves system resilience against transient network failures using robust exponential backoff retries.
* Decouples the node from a specific LLM provider by dynamically resolving the client from the shared state.
* Introduces a strict dependency on the LangChain `ainvoke` interface, causing runtime failures if raw SDK clients are passed in state.
* Truncating long pages to fit LLM context windows may discard valuable information located at the end of documents.

## Alternatives Considered
* **Splitting fetching and summarizing into separate nodes:** Rejected because splitting these tightly coupled operations increases state management overhead and graph complexity.
* **Using a third-party scraping API instead of httpx:** Rejected due to increased external dependency costs and a lack of control over retry behavior.