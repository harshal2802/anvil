# Implementation Plan: Equity Research Agent
**Created:** 2026-05-23
**Complexity:** Medium
**Estimated phases:** 4

## Summary
This plan outlines the development of a 4-node LangGraph agent to automate equity research for GOOGL. The agent sequentially fetches stock price data, gathers upcoming market catalysts, analyzes performance relative to peers, and compiles a structured markdown report validated via Pydantic.

## Phases

### Phase 1: fetch_market_data
**Produces:** one LangGraph node — `fetch_market_data` which fetches 7-day historical price and volume data for GOOGL and its peers.
**Depends on:** nothing
**Risk:** Low — Standard yfinance API calls with robust error handling.
**Prompt:** pdd/prompts/features/equity-research/equity-research-01-fetch-market-data.md

### Phase 2: fetch_catalyst_events
**Produces:** one LangGraph node — `fetch_catalyst_events` which gathers upcoming earnings and macro events for the next 30 days.
**Depends on:** Phase 1
**Risk:** Medium — External API dependencies for macroeconomic calendars can be flaky.
**Prompt:** pdd/prompts/features/equity-research/equity-research-02-fetch-catalyst-events.md

### Phase 3: analyze_and_compare
**Produces:** one LangGraph node — `analyze_and_compare` which calculates percentage changes, aligns timelines, and flags abnormal volume or peer divergence.
**Depends on:** Phase 2
**Risk:** Low — Purely mathematical and logical operations using pandas.
**Prompt:** pdd/prompts/features/equity-research/equity-research-03-analyze-and-compare.md

### Phase 4: generate_report
**Produces:** one LangGraph node — `generate_report` which compiles the final structured markdown report using Gemini Flash and validates it with Pydantic.
**Depends on:** Phase 3
**Risk:** Medium — Ensuring strict schema adherence and neutral tone from the LLM.
**Prompt:** pdd/prompts/features/equity-research/equity-research-04-generate-report.md