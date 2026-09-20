"""Reproducible sampling of candidate tickets."""

import random
from collections.abc import Sequence
from typing import Any, TypeVar

T = TypeVar("T")

DEFAULT_SAMPLE_SIZE = 50
DEFAULT_SEED = 42


def sample_tickets(
    tickets: Sequence[T], size: int = DEFAULT_SAMPLE_SIZE, seed: int = DEFAULT_SEED
) -> list[T]:
    """Pick `size` tickets without replacement. Same input + seed -> same sample, in input order."""
    if size > len(tickets):
        raise ValueError(f"cannot sample {size} tickets from {len(tickets)}")
    positions = sorted(random.Random(seed).sample(range(len(tickets)), size))
    return [tickets[position] for position in positions]


def ticket_ids(tickets: Sequence[dict[str, Any]]) -> list[str]:
    return [ticket["ticket_id"] for ticket in tickets]
