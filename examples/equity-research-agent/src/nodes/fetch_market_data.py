import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, TypedDict
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class GraphState(TypedDict, total=False):
    raw_market_data: Dict[str, Any]
    market_data_fetched_at: str

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((IOError, ValueError)),
    reraise=True
)
def _fetch_ticker_data(ticker: str, start_str: str, end_str: str) -> Dict[str, Any]:
    logger.info(f"Fetching data for {ticker} from {start_str} to {end_str}")
    t = yf.Ticker(ticker)
    df = t.history(start=start_str, end=end_str, interval="1d")
    
    if df.empty:
        raise ValueError(f"No data returned for ticker {ticker} within the window.")
        
    return {
        "dates": [dt.strftime("%Y-%m-%d") for dt in df.index],
        "close": df["Close"].tolist(),
        "volume": df["Volume"].tolist()
    }

async def fetch_market_data(state: GraphState) -> Dict[str, Any]:
    logger.info("Entering fetch_market_data node")
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    tickers = ["GOOGL", "MSFT", "META", "AMZN"]
    raw_data: Dict[str, Any] = {}
    
    for ticker in tickers:
        try:
            # Offload synchronous yfinance network call to a thread pool
            data = await asyncio.to_thread(_fetch_ticker_data, ticker, start_str, end_str)
            raw_data[ticker] = data
        except Exception as err:
            logger.error(f"Failed to fetch data for {ticker} after retries: {err}")
            raise err
            
    logger.info("Successfully fetched market data for all tickers")
    return {
        "raw_market_data": raw_data,
        "market_data_fetched_at": end_date.isoformat()
    }