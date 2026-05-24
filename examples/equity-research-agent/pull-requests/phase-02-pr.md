# feat: add fetch_catalyst_events node for upcoming market events

Labels: enhancement, langgraph, testing

## Summary
- Add a new LangGraph node to retrieve earnings and macro events for the next 30 days.
- Implement Finnhub API integration with structured error handling for API limits and invalid keys.

## Why
We need a structured way to gather upcoming market catalysts to inform downstream trading and analysis nodes. See [docs/adr/002-add-fetch-catalyst-events-node.md](docs/adr/002-add-fetch-catalyst-events-node.md) for the architectural decisions behind this implementation.

## Changes
- `src/nodes/fetch_catalyst_events.py`: Implement the `fetch_catalyst_events` node and the `CatalystFetchError` exception.
- `evals/test_fetch_catalyst_events.py`: Add unit and integration tests to verify API fetching, date calculations, and error states.
- `docs/adr/002-add-fetch-catalyst-events-node.md`: Document the ADR for introducing this node.

## Eval Status
Run `pytest evals/test_fetch_catalyst_events.py` — judge scores populate on first CI run.

## Risk
If the Finnhub API key is missing or invalid, the node raises a `CatalystFetchError` which will halt the LangGraph execution if not caught by parent workflows. API rate limits could also trigger this error during high-frequency runs.

## Reviewer Checklist
- Verify that `CatalystFetchError` is raised when the Finnhub API key is missing from the environment.
- Confirm the date range logic correctly calculates and requests exactly the next 30 days of events.
- Check that the node gracefully handles empty API responses without throwing unhandled exceptions.
- Ensure the tests mock the Finnhub API calls to prevent external network dependency during local test execution.
