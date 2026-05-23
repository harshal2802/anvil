import os
import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from google import genai
from google.genai import types
from node import summarize_url

DATASET = [
    {"id": "happy_1", "input_state": {"url": "https://example.com/blog1"}, "expected_behavior_description": "Fetches blog content and returns a 3-sentence summary.", "category": "happy"},
    {"id": "happy_2", "input_state": {"url": "https://example.com/news1"}, "expected_behavior_description": "Fetches news content and returns a 3-sentence summary.", "category": "happy"},
    {"id": "happy_3", "input_state": {"url": "https://example.com/product1"}, "expected_behavior_description": "Fetches product content and returns a 3-sentence summary.", "category": "happy"},
    {"id": "edge_empty_url", "input_state": {"url": ""}, "expected_behavior_description": "Returns error dict for missing URL.", "category": "edge"},
    {"id": "edge_long_page", "input_state": {"url": "https://example.com/long"}, "expected_behavior_description": "Truncates content and returns a 3-sentence summary.", "category": "edge"},
    {"id": "fail_404_error", "input_state": {"url": "https://example.com/404"}, "expected_behavior_description": "Returns error dict for HTTP 404.", "category": "failure"},
    {"id": "fail_invalid_llm", "input_state": {"url": "https://example.com/blog1", "llm_invalid": True}, "expected_behavior_description": "Raises AttributeError due to invalid LLM client.", "category": "failure"}
]

class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("Error", request=None, response=self)

@pytest.mark.asyncio
@pytest.mark.parametrize("case", DATASET)
async def test_summarize_url(case):
    input_state = case["input_state"]
    url = input_state.get("url")
    mock_llm = AsyncMock()
    if input_state.get("llm_invalid"):
        del mock_llm.ainvoke
    else:
        mock_response = MagicMock()
        mock_response.content = "This is sentence one. This is sentence two. This is sentence three."
        mock_llm.ainvoke.return_value = mock_response
    state = {"url": url, "llm": mock_llm}
    async def mock_get(client, url_arg, **kwargs):
        if "404" in url_arg:
            res = MockResponse("", 404)
            res.raise_for_status()
        elif "long" in url_arg:
            return MockResponse("Long text. " * 2000)
        else:
            return MockResponse("<html><body>Standard content.</body></html>")
    with patch("httpx.AsyncClient.get", mock_get):
        if case["category"] == "failure" and input_state.get("llm_invalid"):
            with pytest.raises(AttributeError):
                await summarize_url(state)
            return
        result = await summarize_url(state)
    judge_client = genai.Client()
    prompt = f"Analyze the following LLM node execution result.\\n\\nInput State: {json.dumps(input_state)}\\nExpected Behavior: {case['expected_behavior_description']}\\nActual Result: {json.dumps(result)}\\n\\nScore the output on three dimensions:\\n1. Correctness (2-4): Does the output match the expected behavior and handle errors correctly?\\n2. Completeness (2-4): Are all required fields present and fully populated?\\n3. Safety (2-4): Is the output safe, free of hallucinations, and robust?\\n\\nRules:\\n- If unsure, score lower and explain. Bias toward catching real defects over false positives.\\n- Compress scores toward the center (avoid 1 and 5). Use 2 for poor, 3 for acceptable, 4 for excellent.\\n- Provide a brief, high-level summary rationale for each score. Keep explanations extremely concise.\\n\\nReturn your response in JSON format:\\n{{\\n    \\"correctness\\": {{\\"score\\": int, \\"rationale\\": \\"string\\"}},\\n    \\"completeness\\": {{\\"score\\": int, \\"rationale\\": \\"string\\"}},\\n    \\"safety\\": {{\\"score\\": int, \\"rationale\\": \\"string\\"}}\\n}}"
    response = judge_client.models.generate_content(model="gemini-2.5-pro", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
    evaluation = json.loads(response.text)
    mean_score = (evaluation["correctness"]["score"] + evaluation["completeness"]["score"] + evaluation["safety"]["score"]) / 3.0
    assert mean_score >= 4.0
    assert evaluation["safety"]["score"] >= 3