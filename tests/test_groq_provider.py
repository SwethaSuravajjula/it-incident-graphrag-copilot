"""Groq adapter mapping, using the real groq response and error types with a fake client."""

from types import SimpleNamespace
from typing import Any

import groq
import httpx
import pytest
from groq.types.chat import ChatCompletion

from src.extraction.groq_provider import GroqProvider, make_provider
from src.extraction.llm import APICallError, FatalAPIError

REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
SCHEMA = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
CALL = dict(model="openai/gpt-oss-120b", system="sys", user="usr", schema=SCHEMA, max_output_tokens=123)


def completion(content: str | None = '{"a": 1}', finish_reason: str = "stop", usage: dict | None = None) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1,
            "model": "openai/gpt-oss-120b",
            "choices": [
                {"index": 0, "finish_reason": finish_reason, "message": {"role": "assistant", "content": content}}
            ],
            "usage": usage,
        }
    )


def status_error(cls: type[groq.APIStatusError], status: int, message: str = "boom") -> groq.APIStatusError:
    return cls(message, response=httpx.Response(status, request=REQUEST), body=None)


class FakeGroq:
    """Stands in for groq.Groq: returns or raises what it was given."""

    def __init__(self, create: Any = None, model_list: Any = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._create = create
        # Default: the one model the tests use is available. Pass an exception to make the call fail.
        self._model_list = model_list if model_list is not None else ["openai/gpt-oss-120b"]
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._do_create))
        self.models = SimpleNamespace(list=self._do_list)

    def _do_create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self._create, Exception):
            raise self._create
        return self._create

    def _do_list(self) -> Any:
        if isinstance(self._model_list, Exception):
            raise self._model_list
        return SimpleNamespace(data=[SimpleNamespace(id=model) for model in self._model_list])


def generate(client: FakeGroq):
    return GroqProvider(client).generate_json(**CALL)


def test_request_uses_strict_json_schema_and_the_token_limit() -> None:
    client = FakeGroq(create=completion())
    generate(client)
    call = client.calls[0]
    assert call["model"] == "openai/gpt-oss-120b"
    assert call["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert call["max_completion_tokens"] == 123
    fmt = call["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"] == SCHEMA


def test_response_and_usage_are_mapped() -> None:
    usage = {
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500,
        "completion_tokens_details": {"reasoning_tokens": 300},
        "prompt_tokens_details": {"cached_tokens": 64},
    }
    llm_result = generate(FakeGroq(create=completion(usage=usage)))
    assert llm_result.text == '{"a": 1}'
    assert (llm_result.finish_reason, llm_result.truncated, llm_result.request_id) == ("stop", False, "chatcmpl-1")
    assert (llm_result.input_tokens, llm_result.output_tokens) == (1000, 500)
    assert (llm_result.thinking_tokens, llm_result.cached_input_tokens) == (300, 64)


def test_missing_usage_counts_as_zero() -> None:
    llm_result = generate(FakeGroq(create=completion(usage=None)))
    assert (llm_result.input_tokens, llm_result.output_tokens) == (0, 0)


def test_length_finish_reason_is_reported_as_truncated() -> None:
    llm_result = generate(FakeGroq(create=completion(content='{"a', finish_reason="length")))
    assert llm_result.truncated is True and llm_result.finish_reason == "length"


def test_empty_content_is_passed_through_as_no_text() -> None:
    assert generate(FakeGroq(create=completion(content=None, finish_reason="tool_calls"))).text is None


@pytest.mark.parametrize(
    ("cls", "status"),
    [(groq.AuthenticationError, 401), (groq.PermissionDeniedError, 403), (groq.NotFoundError, 404)],
)
def test_key_permission_and_model_errors_are_fatal(cls: type[groq.APIStatusError], status: int) -> None:
    with pytest.raises(FatalAPIError, match=str(status)):
        generate(FakeGroq(create=status_error(cls, status)))


@pytest.mark.parametrize(
    ("cls", "status"),
    [(groq.RateLimitError, 429), (groq.InternalServerError, 500), (groq.BadRequestError, 400)],
)
def test_other_api_errors_fail_only_the_ticket(cls: type[groq.APIStatusError], status: int) -> None:
    with pytest.raises(APICallError, match=str(status)):
        generate(FakeGroq(create=status_error(cls, status)))


def test_connection_errors_fail_only_the_ticket() -> None:
    with pytest.raises(APICallError, match="connection error"):
        generate(FakeGroq(create=groq.APIConnectionError(request=REQUEST)))


def test_preflight_accepts_a_model_with_a_slash_in_its_id() -> None:
    GroqProvider(FakeGroq(model_list=["openai/gpt-oss-20b", "openai/gpt-oss-120b"])).check_access("openai/gpt-oss-120b")


def test_preflight_rejects_a_model_the_key_cannot_use_and_lists_the_alternatives() -> None:
    with pytest.raises(FatalAPIError, match="not available.*gpt-oss-20b"):
        GroqProvider(FakeGroq(model_list=["openai/gpt-oss-20b"])).check_access("openai/gpt-oss-120b")


@pytest.mark.parametrize(
    "error",
    [status_error(groq.AuthenticationError, 401), status_error(groq.PermissionDeniedError, 403), groq.APIConnectionError(request=REQUEST)],
)
def test_preflight_failures_are_fatal(error: Exception) -> None:
    with pytest.raises(FatalAPIError):
        GroqProvider(FakeGroq(model_list=error)).check_access("openai/gpt-oss-120b")


def test_make_provider_without_a_key_is_fatal_with_a_helpful_message(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(FatalAPIError, match="GROQ_API_KEY"):
        make_provider()


def test_make_provider_with_a_key_builds_a_provider(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert make_provider().name == "groq"
