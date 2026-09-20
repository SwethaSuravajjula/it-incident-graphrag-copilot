"""Extract structured fields from one candidate ticket with an LLM.

Every ticket ends as either a validated record or a failure record. Nothing is dropped
silently and nothing is repaired: an output that fails validation is reported as a failure
together with the raw model output.
"""

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.extraction.llm import APICallError, LLMProvider
from src.extraction.prompt import SYSTEM_PROMPT, build_user_message
from src.extraction.schema import MODEL_OUTPUT_SCHEMA, validate_extraction
from src.extraction.usage import TokenUsage

logger = logging.getLogger(__name__)

# Includes any reasoning tokens the model spends, so leave headroom over the ~500-token answer.
MAX_OUTPUT_TOKENS = 8000

# Failure stages, in the order they can occur.
STAGE_API_ERROR = "api_error"
STAGE_TRUNCATED = "truncated"
STAGE_NO_OUTPUT = "no_output"
STAGE_INVALID_JSON = "invalid_json"
STAGE_VALIDATION = "validation_error"


@dataclass(frozen=True)
class Outcome:
    """Result for one ticket: exactly one of `record` and `failure` is set."""

    record: dict[str, Any] | None
    failure: dict[str, Any] | None


def _failure(
    ticket_id: str,
    stage: str,
    errors: list[str],
    *,
    raw_output: str | None = None,
    finish_reason: str | None = None,
    request_id: str | None = None,
) -> Outcome:
    logger.warning("ticket %s failed at %s: %s", ticket_id[:12], stage, "; ".join(errors))
    return Outcome(
        record=None,
        failure={
            "ticket_id": ticket_id,
            "stage": stage,
            "errors": errors,
            "raw_output": raw_output,
            "finish_reason": finish_reason,
            "request_id": request_id,
        },
    )


def extract_ticket(
    provider: LLMProvider,
    ticket: Mapping[str, Any],
    *,
    model: str,
    usage: TokenUsage,
) -> Outcome:
    """Call the model for one ticket, then parse and validate its output.

    Raises FatalAPIError for run-wide problems (bad key, permission, unknown model).
    """
    ticket_id = ticket["ticket_id"]
    try:
        result = provider.generate_json(
            model=model,
            system=SYSTEM_PROMPT,
            user=build_user_message(ticket),
            schema=MODEL_OUTPUT_SCHEMA,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
    except APICallError as error:
        return _failure(ticket_id, STAGE_API_ERROR, [str(error)])

    usage.add(result)
    context = {"finish_reason": result.finish_reason, "request_id": result.request_id}

    if result.truncated:
        return _failure(
            ticket_id, STAGE_TRUNCATED, [f"output cut off at {MAX_OUTPUT_TOKENS} tokens"],
            raw_output=result.text, **context,
        )
    if not result.text:
        return _failure(ticket_id, STAGE_NO_OUTPUT, ["response has no text"], **context)

    try:
        payload = json.loads(result.text)
    except json.JSONDecodeError as error:
        return _failure(ticket_id, STAGE_INVALID_JSON, [str(error)], raw_output=result.text, **context)
    if not isinstance(payload, dict):
        return _failure(
            ticket_id, STAGE_INVALID_JSON, [f"expected a JSON object, got {type(payload).__name__}"],
            raw_output=result.text, **context,
        )

    record = {"ticket_id": ticket_id, **payload}
    validation_errors = validate_extraction(
        record, expected_ticket_id=ticket_id, has_answer=bool(ticket.get("answer"))
    )
    if validation_errors:
        return _failure(ticket_id, STAGE_VALIDATION, validation_errors, raw_output=result.text, **context)
    return Outcome(record=record, failure=None)
