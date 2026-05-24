# feat: add analyze and compare node for market data analysis

Labels: feature, langgraph

## Summary
- Introduce a new LangGraph node that calculates percentage changes and aligns timelines across multiple tickers.
- Identify abnormal volume spikes and peer divergence trends in market data.

## Why
We need a structured way to compare multi-ticker market data within the graph execution flow. See [ADR-003](docs/adr/003-add-analyze-and-compare-node.md) for architectural details.

## Changes
- src/nodes/analyze_and_compare.py: Implement the LangGraph node logic for timeline alignment, percentage calculation, and anomaly detection.
- evals/test_analyze_and_compare.py: Add unit and integration tests to verify node output schema and calculation accuracy.
- docs/adr/003-add-analyze-and-compare-node.md: Document the architectural decision for adding this multi-ticker comparison node.

## Eval Status
Run `pytest evals/test_analyze_and_compare.py` — judge scores populate on first CI run.

## Risk
Timeline alignment assumes consistent date string formatting (YYYY-MM-DD) across all tickers. If data sources return mismatched formats or have zero overlapping trading days, the node will fail to find overlaps and return empty datasets.

## Reviewer Checklist
- Verify that the node correctly handles cases where tickers have no overlapping trading days.
- Confirm that percentage calculations handle zero-division errors when starting volume or price is zero.
- Check that the output schema matches the expected LangGraph state transition format.
- Ensure date parsing logic gracefully handles or rejects non-standard date formats instead of throwing unhandled exceptions.
