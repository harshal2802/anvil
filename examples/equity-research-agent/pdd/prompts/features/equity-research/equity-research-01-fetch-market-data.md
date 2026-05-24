# Phase 1: fetch_market_data

## Intent
This node dynamically calculates the 7-day trading window relative to the current execution date. It then fetches historical daily close prices and trading volumes for GOOGL, MSFT, META, and AMZN from yfinance, saving the raw data to the state.

## Inputs
- `current_date`: string (optional, defaults to today's date if not provided)

## Outputs
- `raw_market_data`: dict (mapping ticker symbols to lists of daily close and volume records)
- `execution_error`: string (contains error details if the API call fails)

## Acceptance
- Successfully retrieves exactly 7 trading days of data for GOOGL, MSFT, META, and AMZN.
- Gracefully catches connection timeouts or API rate limits, writing a clear error message to `execution_error`.
- Dynamically resolves the date window without hardcoding any specific calendar year.