"""Groq adapter (OpenAI-compatible chat API) for the extraction experiment."""

import logging
from typing import Any

import groq

from src.extraction.llm import APICallError, FatalAPIError, LLMResult

logger = logging.getLogger(__name__)

# The SDK backs off exponentially and honours the retry-after header on 429s. Groq's free
# tier is limited to a few thousand tokens per minute, so rate limits are expected.
MAX_RETRIES = 5

SCHEMA_NAME = "ticket_extraction"

# Errors that mean the key, its permissions or the model name are wrong for the whole run.
_FATAL_ERRORS = (groq.AuthenticationError, groq.PermissionDeniedError, groq.NotFoundError)


def _describe(error: groq.APIStatusError) -> str:
    return f"HTTP {error.status_code}: {error.message}"


class GroqProvider:
    name = "groq"

    def __init__(self, client: groq.Groq) -> None:
        self._client = client

    def check_access(self, model: str) -> None:
        # Uses the model list rather than models.retrieve(): the SDK URL-encodes the slash in
        # ids like "openai/gpt-oss-120b" and the retrieve endpoint then answers 404.
        try:
            available = sorted(entry.id for entry in self._client.models.list().data)
        except _FATAL_ERRORS as error:
            raise FatalAPIError(_describe(error)) from error
        except groq.APIError as error:
            raise FatalAPIError(f"cannot reach the API: {error}") from error
        if model not in available:
            raise FatalAPIError(f"model {model!r} is not available to this key; available: {available}")

    def generate_json(
        self, *, model: str, system: str, user: str, schema: dict[str, Any], max_output_tokens: int
    ) -> LLMResult:
        try:
            completion = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                # Strict mode constrains decoding to the schema. It is only supported on some models.
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": SCHEMA_NAME, "strict": True, "schema": schema},
                },
                max_completion_tokens=max_output_tokens,
            )
        except _FATAL_ERRORS as error:
            raise FatalAPIError(_describe(error)) from error
        except groq.APIStatusError as error:
            raise APICallError(_describe(error)) from error
        except groq.APIConnectionError as error:  # includes timeouts
            raise APICallError(f"connection error: {error}") from error

        choice = completion.choices[0] if completion.choices else None
        finish_reason = choice.finish_reason if choice is not None else None
        usage = completion.usage
        completion_details = getattr(usage, "completion_tokens_details", None)
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        return LLMResult(
            text=choice.message.content if choice is not None else None,
            finish_reason=finish_reason,
            truncated=finish_reason == "length",
            request_id=completion.id,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            thinking_tokens=getattr(completion_details, "reasoning_tokens", 0) or 0,
            cached_input_tokens=getattr(prompt_details, "cached_tokens", 0) or 0,
        )


def make_provider(api_key: str | None = None) -> GroqProvider:
    """Create the Groq adapter. Without `api_key` the SDK reads GROQ_API_KEY from the environment."""
    try:
        client = groq.Groq(api_key=api_key, max_retries=MAX_RETRIES)
    except groq.GroqError as error:  # raised when no API key is configured
        raise FatalAPIError("no credentials: set GROQ_API_KEY in .env (see .env.example)") from error
    return GroqProvider(client)
