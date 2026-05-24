# feat: add fetch_market_data node for tech equity prices

Labels: feature, data-ingestion

## Summary
- Calculates a rolling 7-day trading window relative to the execution date.
- Fetches daily close prices and trading volumes for GOOGL, MSFT, META, and AMZN using yfinance.
- Saves the raw historical market data to the pipeline state.

## Why
We need a reliable source of recent tech equity performance to feed downstream analysis nodes. See [docs/adr/001-fetch-market-data.md](docs/adr/001-fetch-market-data.md) for architectural decisions.

## Changes
- `src/nodes/fetch_market_data.py`: Implements the fetch_market_data node to calculate the 7-day window and fetch ticker data from yfinance.
- `evals/test_fetch_market_data.py`: Adds unit and integration tests to verify date calculations and yfinance API integration.
- `docs/adr/001-fetch-market-data.md`: Documents the architectural decision to use yfinance for retrieving 7-day tech equity market data.

## Eval Status
Run `pytest evals/test_fetch_market_data.py` — judge scores populate on first CI run.

## Risk
The node relies on yfinance, which is an unofficial scraper. If Yahoo Finance changes its endpoints or rate-limits the execution environment's IP address, the node will fail to fetch data or return empty DataFrames, breaking downstream nodes.

## Reviewer Checklist
- Verify that the 7-day date window calculation correctly handles weekends and holidays.
- Confirm that the yfinance API call handles empty responses or network timeouts gracefully without crashing the pipeline.
- Check that the retrieved close prices and volumes for GOOGL, MSFT, META, and AMZN are correctly formatted and saved to the state.
- Ensure the tests mock yfinance API calls to prevent flaky test runs during CI.
