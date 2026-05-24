## ADR-003: Add analyze_and_compare node for multi-ticker market data analysis
**Status:** Proposed
**Date:** 2026-05-23

## Context
The existing graph fetches raw market data and catalyst events via fetch_market_data and fetch_catalyst_events but lacks a mechanism to synthesize these datasets. Downstream consumers require normalized metrics, timeline alignment, and statistical anomaly detection to make informed decisions. Without a dedicated processing step, raw data remains fragmented across different temporal scales and tickers.

## Decision
We will add the analyze_and_compare node to the LangGraph workflow. This node will ingest raw market data and tickers from the state, align their timelines using date intersections, and calculate comparative metrics such as percentage changes and peer divergence. The output will be persisted in the state under market_analysis_results.

## Consequences
* Centralizes timeline alignment and statistical calculations, preventing duplicate parsing logic in downstream nodes.
* Enables early detection of abnormal market activity and peer divergence before decision-making steps.
* The timeline alignment relies on strict date string format consistency (e.g., YYYY-MM-DD) and will fail or return empty datasets if tickers do not share overlapping trading days.
* Increases memory footprint in the state by storing aligned, multi-ticker historical datasets.

## Alternatives Considered
* Perform analysis on-the-fly within downstream visualization or LLM generation nodes. Rejected because it violates the single-responsibility principle and duplicates heavy statistical logic.
* Do not build this node and rely on external API services for pre-aligned comparative metrics. Rejected due to increased external API costs, latency, and reduced flexibility in defining custom divergence thresholds.