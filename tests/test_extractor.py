"""Extractor and runner behaviour with a fake provider: no network, no key, no cost."""

import json
from typing import Any

import pytest

from src.extraction import run_sample
from src.extraction.extractor import extract_ticket
from src.extraction.llm import APICallError, FatalAPIError, LLMResult
from src.extraction.prompt import MISSING, build_user_message
from src.extraction.sampling import sample_tickets
from src.extraction.usage import TokenUsage, estimate_cost_usd

MODEL = "openai/gpt-oss-120b"

TICKET = {
    "ticket_id": "c" * 64,
    "subject": "VPN drops",
    "body": "The VPN disconnects every hour.",
    "answer": "Please restart the client.",
}

GOOD_OUTPUT = {
    "is_technical_incident": True,
    "systems": ["VPN"],
    "symptoms": ["disconnects every hour"],
    "issues": ["network connectivity failure"],
    "possible_causes": [],
    "support_actions": [{"action": "Asks to restart the client", "action_type": "troubleshooting"}],
}


def result(text: str | None, finish_reason: str = "stop", truncated: bool = False) -> LLMResult:
    return LLMResult(
        text=text, finish_reason=finish_reason, truncated=truncated, request_id="req_test",
        input_tokens=1000, output_tokens=500, thinking_tokens=300, cached_input_tokens=0,
    )


def good(**overrides: Any) -> LLMResult:
    return result(json.dumps({**GOOD_OUTPUT, **overrides}))


class FakeProvider:
    """Returns (or raises) queued items, one per `generate_json` call."""

    name = "fake"

    def __init__(self, *items: Any, access_error: Exception | None = None) -> None:
        self._items = list(items)
        self._access_error = access_error
        self.calls: list[dict[str, Any]] = []

    def check_access(self, model: str) -> None:
        if self._access_error is not None:
            raise self._access_error

    def generate_json(self, **kwargs: Any) -> LLMResult:
        self.calls.append(kwargs)
        item = self._items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def extract(provider: FakeProvider, ticket: dict = TICKET) -> Any:
    return extract_ticket(provider, ticket, model=MODEL, usage=TokenUsage())


def write_candidates(tmp_path, tickets: list[dict]):
    path = tmp_path / "candidates.jsonl"
    path.write_text("".join(json.dumps(t) + "\n" for t in tickets), encoding="utf-8")
    return path


def test_valid_output_becomes_a_record_with_the_code_supplied_ticket_id() -> None:
    outcome = extract(FakeProvider(good()))
    assert outcome.failure is None
    assert outcome.record == {"ticket_id": TICKET["ticket_id"], **GOOD_OUTPUT}


def test_request_carries_the_schema_the_ticket_text_and_the_model() -> None:
    provider = FakeProvider(good())
    extract(provider)
    call = provider.calls[0]
    assert call["model"] == MODEL
    assert call["schema"]["required"][0] == "is_technical_incident"
    assert "The VPN disconnects every hour." in call["user"]
    assert "JSON" in call["system"]


def test_usage_is_accumulated_even_when_the_output_is_rejected() -> None:
    usage = TokenUsage()
    extract_ticket(FakeProvider(result("not json")), TICKET, model=MODEL, usage=usage)
    assert (usage.input_tokens, usage.output_tokens, usage.thinking_tokens, usage.requests) == (1000, 500, 300, 1)


@pytest.mark.parametrize(
    ("llm_result", "stage"),
    [
        (result("not json"), "invalid_json"),
        (result("[1, 2]"), "invalid_json"),
        (result(None), "no_output"),
        (result("", finish_reason="tool_calls"), "no_output"),
        (result('{"is_technical', finish_reason="length", truncated=True), "truncated"),
        (good(issues="a string"), "validation_error"),
        (result(json.dumps({**GOOD_OUTPUT, "extra": 1})), "validation_error"),
    ],
)
def test_bad_outputs_become_failures_not_drops(llm_result: LLMResult, stage: str) -> None:
    outcome = extract(FakeProvider(llm_result))
    assert outcome.record is None
    assert outcome.failure["stage"] == stage
    assert outcome.failure["ticket_id"] == TICKET["ticket_id"]
    assert outcome.failure["request_id"] == "req_test"


def test_failed_validation_keeps_the_raw_output_and_finish_reason() -> None:
    bad = good(issues="a string")
    outcome = extract(FakeProvider(bad))
    assert outcome.failure["raw_output"] == bad.text
    assert outcome.failure["finish_reason"] == "stop"


def test_actions_for_a_ticket_without_an_answer_fail_validation() -> None:
    outcome = extract(FakeProvider(good()), {**TICKET, "answer": None})
    assert outcome.failure["stage"] == "validation_error"


def test_a_failed_call_is_a_failure_record_not_an_abort() -> None:
    outcome = extract(FakeProvider(APICallError("HTTP 429: rate limited")))
    assert outcome.failure["stage"] == "api_error"
    assert "429" in outcome.failure["errors"][0]


def test_fatal_errors_propagate_and_abort() -> None:
    with pytest.raises(FatalAPIError):
        extract(FakeProvider(FatalAPIError("HTTP 401")))


def test_missing_fields_are_marked_in_the_prompt_not_omitted() -> None:
    message = build_user_message({"subject": None, "body": "Body text", "answer": ""})
    assert message == f"SUBJECT:\n{MISSING}\n\nBODY:\nBody text\n\nANSWER:\n{MISSING}"


def test_prompt_leaves_out_metadata_that_could_bias_causes() -> None:
    message = build_user_message({**TICKET, "all_tags": ["Outage"], "queue": "IT Support", "priority": "high"})
    assert "Outage" not in message and "IT Support" not in message


def test_sampling_is_reproducible_and_keeps_input_order() -> None:
    tickets = list(range(1000))
    first = sample_tickets(tickets, size=50, seed=7)
    assert first == sample_tickets(tickets, size=50, seed=7)
    assert first == sorted(first) and len(set(first)) == 50
    assert first != sample_tickets(tickets, size=50, seed=8)


def test_sampling_more_than_available_is_an_error() -> None:
    with pytest.raises(ValueError):
        sample_tickets([1, 2, 3], size=5)


def test_cost_estimate_uses_model_prices_and_is_none_for_unknown_models() -> None:
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    assert estimate_cost_usd("openai/gpt-oss-120b", usage) == 0.75
    assert estimate_cost_usd("some-future-model", usage) is None


def test_run_writes_results_failures_and_manifest_and_counts_them(tmp_path) -> None:
    tickets = [{**TICKET, "ticket_id": f"{i}" * 64} for i in range(3)]
    provider = FakeProvider(good(), good(is_technical_incident=False), result("not json"))

    manifest = run_sample.run(write_candidates(tmp_path, tickets), tmp_path / "out", size=3, seed=1, model=MODEL, provider=provider)

    assert (manifest["technical"], manifest["non_technical"], manifest["failed"]) == (1, 1, 1)
    assert manifest["failures_by_stage"] == {"invalid_json": 1}
    assert manifest["aborted"] is None
    assert manifest["provider"] == "fake"
    assert len(manifest["sample"]["ticket_ids"]) == 3
    assert manifest["usage"]["requests"] == 3
    results = (tmp_path / "out" / "extracted_tickets_sample.jsonl").read_text().splitlines()
    failures = (tmp_path / "out" / "extracted_tickets_sample_failures.jsonl").read_text().splitlines()
    assert (len(results), len(failures)) == (2, 1)


def test_run_without_credentials_aborts_before_touching_any_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    out = tmp_path / "out"
    out.mkdir()
    existing = out / "extracted_tickets_sample.jsonl"
    existing.write_text("earlier results\n", encoding="utf-8")

    with pytest.raises(run_sample.RunAborted, match="no credentials"):
        run_sample.run(write_candidates(tmp_path, [TICKET]), out, size=1, seed=1, model=MODEL)

    assert existing.read_text() == "earlier results\n"
    assert not (out / "extracted_tickets_sample_manifest.json").exists()


def test_run_with_a_rejected_key_or_model_aborts_before_touching_any_file(tmp_path) -> None:
    provider = FakeProvider(access_error=FatalAPIError("HTTP 404: model not found"))
    with pytest.raises(run_sample.RunAborted, match="model not found"):
        run_sample.run(write_candidates(tmp_path, [TICKET]), tmp_path / "out", size=1, seed=1, model=MODEL, provider=provider)
    assert not (tmp_path / "out").exists()


def test_run_stops_after_repeated_api_errors_and_records_each_failure(tmp_path) -> None:
    tickets = [{**TICKET, "ticket_id": f"{i}" * 64} for i in range(8)]
    provider = FakeProvider(*[APICallError("HTTP 429: quota exhausted") for _ in range(8)])

    manifest = run_sample.run(write_candidates(tmp_path, tickets), tmp_path / "out", size=8, seed=1, model=MODEL, provider=provider)

    assert manifest["failed"] == run_sample.MAX_CONSECUTIVE_API_ERRORS == len(provider.calls)
    assert "consecutive API errors" in manifest["aborted"]


def test_a_fatal_error_mid_run_keeps_what_finished_and_records_the_abort(tmp_path) -> None:
    tickets = [{**TICKET, "ticket_id": f"{i}" * 64} for i in range(3)]
    provider = FakeProvider(good(), FatalAPIError("HTTP 401: key revoked"))

    manifest = run_sample.run(write_candidates(tmp_path, tickets), tmp_path / "out", size=3, seed=1, model=MODEL, provider=provider)

    assert (manifest["extracted"], manifest["failed"]) == (1, 0)
    assert "key revoked" in manifest["aborted"]
