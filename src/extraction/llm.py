"""Provider-neutral types between the extractor and an LLM API adapter.

The extractor only knows this interface. Everything specific to one vendor's SDK
(request shape, error classes, usage fields) lives in that vendor's adapter module,
so changing provider means writing one adapter, not touching the extractor.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMResult:
    """One completed API call."""

    text: str | None
    finish_reason: str | None  # the provider's own stop reason, kept for the failure records
    truncated: bool  # the output stopped at the token limit
    request_id: str | None
    input_tokens: int = 0
    output_tokens: int = 0  # everything billed as output, including reasoning tokens
    thinking_tokens: int = 0  # part of output_tokens, reported for visibility
    cached_input_tokens: int = 0  # part of input_tokens, reported for visibility


class APICallError(Exception):
    """One call failed (rate limit after retries, server error, timeout, rejected request).

    The ticket becomes a failure record and the run continues.
    """


class FatalAPIError(Exception):
    """A run-wide problem (no or bad key, no permission, unknown model). The run stops."""


class LLMProvider(Protocol):
    name: str

    def check_access(self, model: str) -> None:
        """Cheap preflight. Raises FatalAPIError if the key or model name cannot be used."""

    def generate_json(
        self, *, model: str, system: str, user: str, schema: dict[str, Any], max_output_tokens: int
    ) -> LLMResult:
        """Ask for one JSON object matching `schema`. Raises APICallError or FatalAPIError."""
