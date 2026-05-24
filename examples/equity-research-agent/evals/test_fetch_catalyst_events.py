import os
import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch
import google.generativeai as genai

try:
    from fetch_catalyst_events import fetch_catalyst_events, CatalystFetchError
except ImportError:
    import sys
    sys.path.append(os.getcwd())
    from main import fetch_catalyst_events, CatalystFetchError

GOLDEN_DATASET = """{"id": "happy_path_standard", "input_state": {"tickers": ["AAPL", "MSFT"]}, "env_vars": {"FINNHUB_API_KEY": "mock_key_123"}, "mock_response": {"status": 200, "earnings": {"earningsCalendar": [{"symbol": "AAPL", "date": "2023-10-25"}, {"symbol": "GOOG", "date": "2023-10-26"}]}, "economic": {"economicCalendar": [{"event": "CPI YoY", "time": "2023-10-12"}]}}, "expected_behavior_description": "Should return catalyst_events containing earnings filtered only for AAPL, and macro events containing CPI YoY.", "category": "happy"}
{"id": "happy_path_empty_tickers", "input_state": {"tickers": []}, "env_vars": {"FINNHUB_API_KEY": "mock_key_123"}, "mock_response": {"status": 200, "earnings": {"earningsCalendar": [{"symbol": "AAPL", "date": "2023-10-25"}]}, "economic": {"economicCalendar": [{"event": "FOMC Meeting"}]}}, "expected_behavior_description": "Should return all earnings events (AAPL) and macro events (FOMC Meeting) because tickers list is empty.", "category": "happy"}
{"id": "happy_path_single_ticker", "input_state": {"tickers": ["TSLA"]}, "env_vars": {"FINNHUB_API_KEY": "mock_key_123"}, "mock_response": {"status": 200, "earnings": {"earningsCalendar": [{"symbol": "TSLA", "date": "2023-10-20"}, {"symbol": "MSFT", "date": "2023-10-24"}]}, "economic": {"economicCalendar": []}}, "expected_behavior_description": "Should return earnings filtered to TSLA only, and empty macro events.", "category": "happy"}
{"id": "edge_case_invalid_tickers", "input_state": {"tickers": ["INVALID_TICKER_XYZ"]}, "env_vars": {"FINNHUB_API_KEY": "mock_key_123"}, "mock_response": {"status": 200, "earnings": {"earningsCalendar": [{"symbol": "AAPL", "date": "2023-10-25"}]}, "economic": {"economicCalendar": [{"event": "GDP Growth"}]}}, "expected_behavior_description": "Should return empty earnings list (since no earnings match the invalid ticker) and successfully return the macro events.", "category": "edge"}
{"id": "edge_case_long_tickers", "input_state": {"tickers": ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10"]}, "env_vars": {"FINNHUB_API_KEY": "mock_key_123"}, "mock_response": {"status": 200, "earnings": {"earningsCalendar": [{"symbol": "T1", "date": "2023-10-25"}, {"symbol": "T11", "date": "2023-10-26"}]}, "economic": {"economicCalendar": []}}, "expected_behavior_description": "Should handle a long list of tickers, filtering earnings to only include T1, and return empty macro events.", "category": "edge"}
{"id": "failure_mode_missing_api_key", "input_state": {"tickers": ["AAPL"]}, "env_vars": {}, "mock_response": {"status": 200, "earnings": {}, "economic": {}}, "expected_behavior_description": "Should raise a ValueError stating that FINNHUB_API_KEY environment variable must be set.", "category": "failure"}
{"id": "failure_mode_api_error", "input_state": {"tickers": ["AAPL"]}, "env_vars": {"FINNHUB_API_KEY": "mock_key_123"}, "mock_response": {"status": 500, "earnings": {}, "economic": {}}, "expected_behavior_description": "Should raise a CatalystFetchError due to API failure (500 Internal Server Error).", "category": "failure"}"""

class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Error {self.status_code}",
                request=httpx.Request("GET", "https://finnhub.io"),
                response=httpx.Response(self.status_code)
            )

@pytest.mark.asyncio
@pytest.mark.parametrize("case_str", GOLDEN_DATASET.strip().split("\n"))
async def test_fetch_catalyst_events_node(case_str):
    case = json.loads(case_str)
    input_state = case["input_state"]
    env_vars = case["env_vars"]
    mock_response = case["mock_response"]
    expected_behavior = case["expected_behavior_description"]

    with patch.dict(os.environ, env_vars, clear=True):
        async def mock_get(url, params=None, timeout=10.0):
            status = mock_response["status"]
            if "earnings" in str(url):
                return MockResponse(status, mock_response["earnings"])
            elif "economic" in str(url):
                return MockResponse(status, mock_response["economic"])
            return MockResponse(404, {})

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_client_get:
            mock_client_get.side_effect = mock_get

            actual_output = None
            error_raised = None

            try:
                actual_output = await fetch_catalyst_events(input_state)
            except Exception as e:
                error_raised = f"{type(e).__name__}: {str(e)}"

            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                pytest.fail("GEMINI_API_KEY environment variable is missing. Cannot run LLM evaluation.")

            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel("gemini-2.5-pro")

            prompt = f"""
You are an LLM evaluation judge. Your task is to evaluate the output of a LangGraph node named `fetch_catalyst_events`.
The node fetches upcoming earnings and macro events for the next 30 days.

### Evaluation Context:
- **Input State**: {json.dumps(input_state)}
- **Expected Behavior**: {expected_behavior}
- **Actual Output State**: {json.dumps(actual_output) if actual_output else "None"}
- **Error Raised (if any)**: {error_raised if error_raised else "None"}

### Rubric:
1. Correctness (1-5):
   - 5: Output matches expected behavior perfectly. Correct exception class and message if expected, or correct filtering and structure if data expected.
   - 4: Minor deviations that do not affect the main functionality.
   - 3: Moderate deviations, some incorrect filtering or slightly off error handling.
   - 2: Major deviations, incorrect behavior or wrong exception raised.
   - 1: Completely incorrect behavior or crashed unexpectedly.

2. Completeness (1-5):
   - 5: All expected fields (`fetched_at`, `timeframe_days`, `earnings`, `macro`) are present and fully populated according to the input state and mock data.
   - 4: Minor missing metadata but core data is complete.
   - 3: Some expected events are missing or extra unfiltered events are present.
   - 2: Major missing data components.
   - 1: Empty or completely missing response payload.

3. Safety (1-5):
   - 5: No sensitive data (like API keys) is leaked in the output or error messages. Handles missing keys and API failures gracefully without exposing stack traces or raw credentials.
   - 4: Safe, but error messages could be slightly more sanitized.
   - 3: No direct leak, but potential for exposing internal system details under specific conditions.
   - 2: Leaks minor system details or raw request parameters.
   - 1: Leaks sensitive credentials (e.g., API keys) or raw stack traces in the returned state.

### Instructions:
- If unsure, score lower and explain. Bias toward catching real defects over false positives.
- Return your evaluation strictly as a JSON object with the following structure:
{{
  "correctness": {{
    "score": <int>,
    "rationale": "<string>"
  }},
  "completeness": {{
    "score": <int>,
    "rationale": "<string>"
  }},
  "safety": {{
    "score": <int>,
    "rationale": "<string>"
  }}
}}
Do not include any other text, markdown formatting, or backticks.
"""
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            try:
                evaluation = json.loads(response_text)
            except Exception as e:
                pytest.fail(f"Failed to parse judge response as JSON: {response.text}. Error: {e}")

            correctness_score = evaluation["correctness"]["score"]
            completeness_score = evaluation["completeness"]["score"]
            safety_score = evaluation["safety"]["score"]
            mean_score = (correctness_score + completeness_score + safety_score) / 3.0

            assert mean_score >= 4.0, f"Mean score {mean_score:.2f} is below the threshold of 4.0. Rationale: {evaluation}"
            assert safety_score >= 3, f"Safety score {safety_score} is below the threshold of 3. Rationale: {evaluation['safety']['rationale']}"
