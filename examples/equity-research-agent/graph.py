from __future__ import annotations
from typing import Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

from src.nodes.fetch_market_data import fetch_market_data
from src.nodes.fetch_catalyst_events import fetch_catalyst_events
from src.nodes.analyze_and_compare import analyze_and_compare
from src.nodes.generate_report import generate_report

class GraphState(TypedDict):
    raw_market_data: Dict[str, Any]
    market_data_fetched_at: str
    tickers: List[str]
    catalyst_events: Dict[str, Any]
    market_analysis_results: Dict[str, Any]
    final_report_markdown: str
    final_report_structured: Dict[str, Any]

builder = StateGraph(GraphState)

builder.add_node("fetch_market_data", fetch_market_data)
builder.add_node("fetch_catalyst_events", fetch_catalyst_events)
builder.add_node("analyze_and_compare", analyze_and_compare)
builder.add_node("generate_report", generate_report)

builder.add_edge(START, "fetch_market_data")
builder.add_edge("fetch_market_data", "fetch_catalyst_events")
builder.add_edge("fetch_catalyst_events", "analyze_and_compare")
builder.add_edge("analyze_and_compare", "generate_report")
builder.add_edge("generate_report", END)

graph = builder.compile()