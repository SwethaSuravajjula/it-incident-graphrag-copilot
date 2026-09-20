"""Token usage tracking and cost estimation for extraction runs."""

from dataclasses import asdict, dataclass

from src.extraction.llm import LLMResult

# USD per million tokens (input, output), Groq on-demand pricing, read from
# https://console.groq.com/docs/models on 2026-09-20. Check it before relying on these.
# Only models with a price found there are listed; any other model reports no estimate.
PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "openai/gpt-oss-20b": (0.075, 0.30),
    "openai/gpt-oss-120b": (0.15, 0.60),
}


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0  # includes reasoning tokens: what is billed as output
    thinking_tokens: int = 0  # part of output_tokens, reported for visibility
    cached_input_tokens: int = 0  # part of input_tokens, reported for visibility
    requests: int = 0

    def add(self, result: LLMResult) -> None:
        self.input_tokens += result.input_tokens
        self.output_tokens += result.output_tokens
        self.thinking_tokens += result.thinking_tokens
        self.cached_input_tokens += result.cached_input_tokens
        self.requests += 1

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def estimate_cost_usd(model: str, usage: TokenUsage) -> float | None:
    """Estimated cost in USD, or None when the model has no known price.

    Every prompt token is priced at the full input rate, so this is an upper bound when
    the API served part of the prompt from a cheaper cache.
    """
    prices = PRICING_PER_MTOK.get(model)
    if prices is None:
        return None
    input_price, output_price = prices
    return round((usage.input_tokens * input_price + usage.output_tokens * output_price) / 1_000_000, 4)
