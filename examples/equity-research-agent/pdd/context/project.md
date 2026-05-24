# Project: Equity Research Agent

## What we're building
An automated, LangGraph-powered financial research assistant that analyzes Google's (GOOGL) stock price action over the last 7 trading days. The agent aggregates historical price data, compares performance against key peers (such as Microsoft, Meta, and Amazon), and compiles a chronological calendar of upcoming earnings announcements and market-moving events.

## Who it's for
- **Retail Investors**: Individuals seeking a consolidated, data-backed summary of recent stock movements and upcoming catalysts without manually checking multiple financial portals.
- **Financial Analysts**: Professionals looking to automate the initial data-gathering and peer-comparison phase of their daily market preparation.

## Tech stack
- Python 3.11+
- LangGraph 0.2+
- Gemini Flash (via langchain-google-genai)
- yfinance (for fetching historical stock data and peer metrics)
- pandas (for data alignment, percentage change calculations, and tabular formatting)
- pydantic (for strict schema validation of the final research report)
- httpx (for querying external macroeconomic and earnings calendars)

## What good output looks like
- A structured markdown report containing a clean table of GOOGL's daily close, volume, and percentage change over the last 7 trading days.
- A peer comparison table displaying the relative performance (percentage change) of GOOGL against MSFT, META, and AMZN over the same 7-day window.
- A chronological list of upcoming earnings dates, dividend dates, or relevant macroeconomic events (e.g., Fed meetings) scheduled within the next 30 days.
- A concise, bulleted executive summary highlighting any abnormal volume or price divergence between GOOGL and its peers.

## Constraints
- Never hallucinate or estimate stock prices; all financial metrics must be sourced directly from live API calls to yfinance or verified external endpoints.
- Never provide investment advice, buy/sell ratings, or price targets; the agent must maintain a strictly neutral, analytical tone.
- Never fail silently on API rate limits or connection errors; the agent must catch exceptions and output a clear error state detailing which data source failed.
- Never hardcode the current date; always resolve the current date dynamically to ensure the 7-day trading window is calculated accurately relative to the execution timestamp.

## Current state
Greenfield. Scaffolded via anvil init on 2026-05-23. No nodes implemented yet.