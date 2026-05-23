from __future__ import annotations

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from src.nodes.summarize_url_node import summarize_url

class GraphState(TypedDict):
    url: str
    summary: str | None
    error: str | None
    llm: object

builder = StateGraph(GraphState)
builder.add_node("summarize_url", summarize_url)
builder.add_edge(START, "summarize_url")
builder.add_edge("summarize_url", END)

graph = builder.compile()