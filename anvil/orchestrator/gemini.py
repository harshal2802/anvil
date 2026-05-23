"""Gemini Flash client wrapper.

Thin layer around google-genai's async client. Reads the API key from env,
calls generate_content with structured output, returns the parsed pydantic
model. Retries with exponential backoff on transient failures.
"""

from __future__ import annotations

import logging
import os
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.environ.get("ANVIL_MODEL", "gemini-3.5-flash")

T = TypeVar("T", bound=BaseModel)


class GeminiAuthError(RuntimeError):
    """GOOGLE_API_KEY (or GEMINI_API_KEY) is missing from the environment."""


class GeminiResponseError(RuntimeError):
    """Flash returned a response that could not be parsed as the requested schema."""


def _client() -> genai.Client:
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiAuthError(
            "GOOGLE_API_KEY (or GEMINI_API_KEY) must be set to call Gemini Flash. "
            "Get one at https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
async def run_agent(
    *,
    system_instruction: str,
    user_message: str,
    response_schema: type[T],
    temperature: float,
    model: str = DEFAULT_MODEL,
) -> T:
    """Call Gemini Flash with structured output. Returns the parsed pydantic model."""
    logger.info(
        "flash.run agent=%s temp=%s model=%s",
        response_schema.__name__,
        temperature,
        model,
    )
    response = await _client().aio.models.generate_content(
        model=model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=temperature,
        ),
    )
    parsed = response.parsed
    if parsed is None:
        raw = (response.text or "")[:500]
        raise GeminiResponseError(f"Flash returned unparseable output: {raw}")
    return parsed  # type: ignore[return-value]
