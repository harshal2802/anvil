import os
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

class GraphState(TypedDict):
    raw_market_data: Dict[str, Any]
    market_data_fetched_at: str
    tickers: List[str]
    catalyst_events: Dict[str, Any]

class CatalystFetchError(Exception):
    """Raised when fetching catalyst events fails after retries."""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def _fetch_from_api(
    client: httpx.AsyncClient, 
    url: str, 
    params: Dict[str, Any]
) -> Dict[str, Any]:
    response = await client.get(url, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()

async def fetch_catalyst_events(state: GraphState) -> Dict[str, Any]:
    logger.info("Entering fetch_catalyst_events node")
    
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        logger.error("FINNHUB_API_KEY environment variable is missing")
        raise ValueError("FINNHUB_API_KEY environment variable must be set")

    tickers = state.get("tickers", [])
    
    start_date = datetime.utcnow().date()
    end_date = start_date + timedelta(days=30)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    earnings_url = "https://finnhub.io/api/v1/calendar/earnings"
    economic_url = "https://finnhub.io/api/v1/calendar/economic"
    
    earnings_events: List[Dict[str, Any]] = []
    economic_events: List[Dict[str, Any]] = []
    
    async with httpx.AsyncClient() as client:
        try:
            economic_data = await _fetch_from_api(
                client, 
                economic_url, 
                {"from": start_str, "to": end_str, "token": api_key}
            )
            economic_events = economic_data.get("economicCalendar", [])
        except Exception as exc:
            logger.error(f"Failed to fetch economic calendar: {exc}")
            raise CatalystFetchError("Failed to fetch economic calendar events") from exc

        try:
            earnings_data = await _fetch_from_api(
                client, 
                earnings_url, 
                {"from": start_str, "to": end_str, "token": api_key}
            )
            raw_earnings = earnings_data.get("earningsCalendar", [])
            
            if tickers:
                ticker_set = set(tickers)
                earnings_events = [
                    event for event in raw_earnings 
                    if event.get("symbol") in ticker_set
                ]
            else:
                earnings_events = raw_earnings
        except Exception as exc:
            logger.error(f"Failed to fetch earnings calendar: {exc}")
            raise CatalystFetchError("Failed to fetch earnings calendar events") from exc

    logger.info(
        f"Successfully fetched {len(earnings_events)} earnings events and "
        f"{len(economic_events)} economic events for the next 30 days"
    )
    
    return {
        "catalyst_events": {
            "fetched_at": datetime.utcnow().isoformat(),
            "timeframe_days": 30,
            "earnings": earnings_events,
            "macro": economic_events
        }
    }