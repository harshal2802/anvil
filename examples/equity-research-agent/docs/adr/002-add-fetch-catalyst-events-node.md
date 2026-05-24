## ADR-002: Add fetch_catalyst_events node to gather upcoming market catalysts
**Status:** Proposed
**Date:** 2026-05-23

## Context
The existing fetch_market_data node retrieves historical and current price data, but lacks forward-looking context regarding macro events and corporate earnings. To make informed trading or analysis decisions, the graph needs a mechanism to ingest upcoming market catalysts over a 30-day horizon.

## Decision
We will add the fetch_catalyst_events node to the LangGraph workflow. This node will query external financial APIs asynchronously using httpx to retrieve earnings calendars and macro events, appending them to the catalyst_events state key. It will utilize tenacity-based retries to handle transient network issues.

## Consequences
* Provides downstream nodes with critical forward-looking context to adjust risk parameters before major volatility events.
* Isolates external API integration concerns, making it easier to swap data providers in the future.
* Introduces a hard dependency on the Finnhub API and its rate limits, creating a potential failure point if the API key is invalid or exhausted.
* Increases the state size payload stored in the LangGraph state history.

## Alternatives Considered
* **Merge catalyst fetching into fetch_market_data:** Rejected because it violates the single responsibility principle and complicates error recovery for distinct API endpoints.
* **Not building this node:** Rejected because historical data alone cannot predict sudden volatility caused by upcoming earnings releases or macro announcements.