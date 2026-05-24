import logging
from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

logger = logging.getLogger(__name__)

class ReportSection(BaseModel):
    heading: str = Field(description="The heading of this section.")
    content: str = Field(description="The markdown content of this section.")

class MarketReport(BaseModel):
    title: str = Field(description="The title of the market report.")
    executive_summary: str = Field(description="A high-level executive summary of the findings.")
    sections: List[ReportSection] = Field(description="Detailed sections of the report covering market data, catalyst events, and comparative analysis.")
    conclusion: str = Field(description="Final conclusion and outlook.")

class GraphState(TypedDict):
    raw_market_data: Dict[str, Any]
    market_data_fetched_at: str
    tickers: List[str]
    catalyst_events: Dict[str, Any]
    market_analysis_results: Dict[str, Any]
    final_report_markdown: str
    final_report_structured: Dict[str, Any]

def _format_report_to_markdown(report: MarketReport) -> str:
    md = f"# {report.title}\n\n"
    md += f"## Executive Summary\n\n{report.executive_summary}\n\n"
    for section in report.sections:
        md += f"## {section.heading}\n\n{section.content}\n\n"
    md += f"## Conclusion\n\n{report.conclusion}\n"
    return md

async def generate_report(state: GraphState, *, model: Optional[Any] = None) -> Dict[str, Any]:
    logger.info("Entering generate_report node")
    
    active_model = model or state.get("model")
    if not active_model:
        logger.error("No LLM model client provided in state or kwargs")
        raise ValueError("A valid LLM model client must be provided in the state or as a keyword argument.")
    
    tickers = state.get("tickers", [])
    raw_market_data = state.get("raw_market_data", {})
    catalyst_events = state.get("catalyst_events", {})
    market_analysis_results = state.get("market_analysis_results", {})
    
    prompt = (
        f"You are an expert financial analyst. Compile a comprehensive, structured market report for the following tickers: {tickers}.\n\n"
        f"Use the following inputs to build the report:\n"
        f"1. Raw Market Data: {raw_market_data}\n"
        f"2. Catalyst Events: {catalyst_events}\n"
        f"3. Market Analysis & Comparisons: {market_analysis_results}\n\n"
        f"Generate a structured report matching the requested schema. Ensure all markdown content within sections is professional, detailed, and well-formatted."
    )
    
    structured_model = active_model.with_structured_output(MarketReport)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _execute_llm_call() -> MarketReport:
        logger.info("Attempting to call LLM for structured report generation")
        return await structured_model.ainvoke(prompt)
    
    try:
        report_data: MarketReport = await _execute_llm_call()
    except Exception as e:
        logger.error(f"Failed to generate structured report after retries: {e}")
        raise e
        
    markdown_report = _format_report_to_markdown(report_data)
    
    logger.info("Successfully generated and validated market report")
    return {
        "final_report_markdown": markdown_report,
        "final_report_structured": report_data.model_dump()
    }