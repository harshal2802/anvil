import logging
from typing import Any, Dict, List, Set
from statistics import mean, stdev
from datetime import datetime

logger = logging.getLogger(__name__)

async def analyze_and_compare(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes market data across multiple tickers by aligning timelines, 
    calculating percentage changes, and flagging abnormal volume or peer divergence.
    """
    logger.info("Entering analyze_and_compare node")
    
    raw_market_data: Dict[str, Any] = state.get("raw_market_data", {})
    tickers: List[str] = state.get("tickers", [])
    catalyst_events: Dict[str, Any] = state.get("catalyst_events", {})

    if not tickers or not raw_market_data:
        logger.warning("Missing tickers or raw market data. Skipping analysis.")
        return {
            "market_analysis_results": {
                "error": "Missing input data for analysis",
                "aligned_data": {},
                "metrics": {}
            }
        }

    try:
        # Step 1: Align timelines by finding the intersection of dates across all tickers
        ticker_dates: List[Set[str]] = []
        for ticker in tickers:
            ticker_data = raw_market_data.get(ticker, {})
            dates = set(ticker_data.get("dates", []))
            if dates:
                ticker_dates.append(dates)

        if not ticker_dates:
            raise ValueError("No valid dates found in raw market data for alignment.")

        aligned_dates_set = set.intersection(*ticker_dates)
        aligned_dates = sorted(list(aligned_dates_set))

        if not aligned_dates:
            raise ValueError("No overlapping dates found across the specified tickers.")

        # Step 2: Extract and filter aligned series
        aligned_series: Dict[str, Dict[str, List[Any]]] = {}
        for ticker in tickers:
            ticker_data = raw_market_data.get(ticker, {})
            raw_dates: List[str] = ticker_data.get("dates", [])
            raw_closes: List[float] = ticker_data.get("close", [])
            raw_volumes: List[int] = ticker_data.get("volume", [])

            aligned_closes = []
            aligned_volumes = []

            # Map raw data to aligned dates
            date_to_index = {date: idx for idx, date in enumerate(raw_dates)}
            for date in aligned_dates:
                idx = date_to_index[date]
                aligned_closes.append(raw_closes[idx])
                aligned_volumes.append(raw_volumes[idx])

            aligned_series[ticker] = {
                "close": aligned_closes,
                "volume": aligned_volumes
            }

        # Step 3: Calculate metrics and flag anomalies
        analysis_metrics: Dict[str, Any] = {}
        daily_returns: Dict[str, List[float]] = {}

        for ticker in tickers:
            closes = aligned_series[ticker]["close"]
            volumes = aligned_series[ticker]["volume"]

            # Percentage change over the entire aligned period
            total_pct_change = ((closes[-1] - closes[0]) / closes[0]) * 100.0 if closes[0] != 0 else 0.0

            # Daily returns calculation
            ticker_daily_returns = [0.0]
            for i in range(1, len(closes)):
                prev = closes[i - 1]
                curr = closes[i]
                ret = ((curr - prev) / prev) * 100.0 if prev != 0 else 0.0
                ticker_daily_returns.append(ret)
            daily_returns[ticker] = ticker_daily_returns

            # Abnormal volume detection (volume > 1.5 standard deviations above the mean)
            avg_vol = mean(volumes) if volumes else 0
            std_vol = stdev(volumes) if len(volumes) > 1 else 0
            volume_threshold = avg_vol + (1.5 * std_vol)

            abnormal_volume_days = []
            for idx, vol in enumerate(volumes):
                if vol > volume_threshold:
                    abnormal_volume_days.append({
                        "date": aligned_dates[idx],
                        "volume": vol,
                        "average_volume": avg_vol
                    })

            analysis_metrics[ticker] = {
                "total_percentage_change": total_pct_change,
                "average_volume": avg_vol,
                "abnormal_volume_days": abnormal_volume_days,
                "peer_divergence_days": []
            }

        # Step 4: Calculate cohort average daily returns and detect peer divergence
        num_days = len(aligned_dates)
        for day_idx in range(num_days):
            day_returns = [daily_returns[ticker][day_idx] for ticker in tickers]
            cohort_avg_return = mean(day_returns) if day_returns else 0.0

            for ticker in tickers:
                ticker_return = daily_returns[ticker][day_idx]
                # Divergence threshold set to 2.0 percentage points from cohort average
                divergence = ticker_return - cohort_avg_return
                if abs(divergence) > 2.0:
                    date_str = aligned_dates[day_idx]
                    # Correlate with catalyst events if available
                    related_catalysts = catalyst_events.get(ticker, {}).get(date_str, [])
                    
                    analysis_metrics[ticker]["peer_divergence_days"].append({
                        "date": date_str,
                        "ticker_return": ticker_return,
                        "cohort_average_return": cohort_avg_return,
                        "divergence": divergence,
                        "catalysts": related_catalysts
                    })

        results = {
            "aligned_dates": aligned_dates,
            "metrics": analysis_metrics
        }

        logger.info("Successfully completed market data analysis and comparison")
        return {"market_analysis_results": results}

    except Exception as e:
        logger.error(f"Error during market data analysis: {str(e)}", exc_info=True)
        raise e
