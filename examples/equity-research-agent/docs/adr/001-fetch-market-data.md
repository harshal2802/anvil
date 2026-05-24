## ADR-001: Fetch 7-Day Tech Equity Market Data via yfinance
**Status:** Proposed
**Date:** 2026-05-23

## Context
The application requires historical market telemetry for GOOGL, MSFT, META, and AMZN to perform downstream quantitative analysis and portfolio optimization. The existing graph entry point, `load_inputs`, only initializes the execution context and lacks any external market data retrieval capabilities. To enable analytical workflows, we need a reliable mechanism to ingest recent daily close prices and trading volumes.

## Decision
We will add the `fetch_market_data` node immediately following the `load_inputs` node. This node will dynamically calculate a rolling 7-day trading window relative to the current execution date, fetch daily close prices and volumes using the `yfinance` library, and save the raw data to the shared graph state.

## Consequences
* Provides immediate, zero-cost access to historical equity data without requiring API key management or paid subscriptions.
* Implements exponential backoff retries via the `tenacity` library to mitigate transient network errors and minor rate-limiting.
* Introduces significant fragility because `yfinance` relies on unofficial scraping of Yahoo Finance, which can break unexpectedly if upstream endpoints or HTML structures change.
* Increases latency during graph execution due to synchronous HTTP requests to external Yahoo Finance endpoints.

## Alternatives Considered
* Using a premium financial API like Polygon.io or Alpaca: Rejected because it introduces subscription costs and credential management overhead that are unnecessary for the current scope.
* Not building this node and using static mock data: Rejected because downstream analytical nodes require live, dynamic market telemetry to produce meaningful insights.