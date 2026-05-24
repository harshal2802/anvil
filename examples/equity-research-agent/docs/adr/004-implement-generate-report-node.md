## ADR-004: Implement generate_report Node for Structured Markdown Report Generation
**Status:** Proposed
**Date:** 2026-05-23

## Context
The existing LangGraph workflow fetches market data, retrieves catalyst events, and performs comparative analysis across multiple tickers. However, the graph lacks a dedicated component to aggregate these disparate analysis results into a cohesive, validated, and human-readable document for end-users.

## Decision
We will add the `generate_report` node to the LangGraph workflow. This node will ingest the accumulated state, leverage Gemini Flash to populate a structured Pydantic `MarketReport` schema, and serialize the validated data into a standardized Markdown document.

## Consequences
* Guarantees structural integrity and type safety of the final report through Pydantic validation schemas.
* Decouples raw analytical processing from the final presentation-layer formatting.
* Introduces a hard dependency on the LangChain `with_structured_output` interface, which will fail if a raw Gemini SDK client is passed instead of a compatible wrapper.
* Increases overall graph execution latency by introducing an additional LLM generation step at the end of the pipeline.

## Alternatives Considered
* **Formatting inside analyze_and_compare:** Rejected because it violates the single responsibility principle and mixes comparative analysis logic with document generation.
* **Not building this node:** Rejected because downstream consumers require a polished, human-readable markdown document rather than raw, unstructured analysis JSON.