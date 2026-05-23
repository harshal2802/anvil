import logging
from typing import Any, Dict, TypedDict, cast
from bs4 import BeautifulSoup
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

logger = logging.getLogger(__name__)

class GraphState(TypedDict):
    url: str
    summary: str | None
    error: str | None
    llm: Any

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def _fetch_url_content(client: httpx.AsyncClient, url: str) -> str:
    """Fetch raw HTML content from the URL with exponential backoff retries."""
    logger.info(f"Fetching URL: {url}")
    response = await client.get(url, timeout=15.0, follow_redirects=True)
    response.raise_for_status()
    return response.text

async def summarize_url(state: GraphState) -> Dict[str, Any]:
    """Fetches a URL, extracts and truncates its main text, and generates a 3-sentence summary using the LLM."""
    logger.info("Entering summarize_url node")
    url = state.get("url")
    llm = state.get("llm")

    if not url:
        logger.error("No URL found in state")
        return {"error": "Missing URL in state", "summary": None}
    if not llm:
        logger.error("No LLM client found in state")
        return {"error": "Missing LLM client in state", "summary": None}

    try:
        async with httpx.AsyncClient() as client:
            html_content = await _fetch_url_content(client, url)

        # Parse HTML and extract text to handle long pages gracefully
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator=" ")
        # Collapse whitespace
        cleaned_text = " ".join(text.split())

        # Truncate to ~12,000 characters (~3000 tokens) to prevent LLM context overflow
        max_chars = 12000
        truncated_text = cleaned_text[:max_chars] + "..." if len(cleaned_text) > max_chars else cleaned_text
        logger.info(f"Extracted and cleaned text. Length: {len(cleaned_text)} chars. Truncated to: {len(truncated_text)} chars.")

        # Prepare prompt for the LLM
        prompt = (
            "You are a precise summarization assistant. "
            "Read the following web page content and provide a summary that is exactly three sentences long. "
            "Do not write more or less than three sentences.\n\n"
            f"Content:\n{truncated_text}"
        )

        # Invoke LLM. We assume standard LangChain Runnable interface (ainvoke)
        logger.info("Invoking LLM for summarization")
        # We support both string-based and message-based LLM interfaces
        if hasattr(llm, "ainvoke"):
            response = await llm.ainvoke(prompt)
            # Extract content if it's a BaseMessage, otherwise cast to string
            summary = getattr(response, "content", str(response)).strip()
        else:
            raise AttributeError("The provided LLM client does not implement the required 'ainvoke' method.")

        logger.info("Successfully generated summary")
        return {"summary": summary, "error": None}

    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error occurred while fetching URL: {exc}")
        return {"error": f"HTTP error: {exc.response.status_code}", "summary": None}
    except httpx.RequestError as exc:
        logger.error(f"Network request error occurred: {exc}")
        return {"error": f"Network request failed: {exc}", "summary": None}
    except Exception as exc:
        logger.error(f"Unexpected error in summarize_url node: {exc}", exc_info=True)
        # Re-raise unexpected system/code errors to avoid silent failures
        raise exc
