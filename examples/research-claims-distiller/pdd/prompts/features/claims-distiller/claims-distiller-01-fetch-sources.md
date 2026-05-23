# Phase 1: fetch_sources

## Intent
This node reads a list of target URLs from the state, concurrently fetches their HTML content using `httpx.AsyncClient` with a 10-second timeout, parses the text using `beautifulsoup4` to remove boilerplate, and writes the successfully retrieved text and any failed URLs back to the state.

## Inputs
- `urls`: List[str] - The target URLs to fetch.

## Outputs
- `raw_sources`: Dict[str, str] - A mapping of successful URLs to their parsed text content.
- `failed_sources`: List[str] - A list of URLs that failed due to timeouts or HTTP errors.

## Acceptance
- Concurrently fetches all URLs within a strict 10-second timeout per request.
- Uses BeautifulSoup to extract clean text content, discarding scripts, styles, and navigation elements.
- Gracefully handles 4xx/5xx errors and records failed URLs in the state.