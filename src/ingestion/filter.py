"""Deterministic candidate filtering on metadata only.

This selects candidate tickets. It does not decide whether a ticket really is
a technical incident; that is a semantic judgement made later during extraction.
"""

import logging
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any

from src.ingestion.schema import Ticket

logger = logging.getLogger(__name__)

CANDIDATE_LANGUAGE = "en"
CANDIDATE_TICKET_TYPES = frozenset({"Incident", "Problem"})
CANDIDATE_QUEUES = frozenset(
    {
        "Technical Support",
        "IT Support",
        "Service Outages and Maintenance",
        "Product Support",
    }
)

REASON_LANGUAGE = "language_not_en"
REASON_TICKET_TYPE = "ticket_type_not_incident_or_problem"
REASON_QUEUE = "queue_not_candidate"


@dataclass
class FilterResult:
    candidates: list[Ticket] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)


def rejection_reasons(ticket: Ticket) -> list[str]:
    """Every filter a ticket fails. An empty list means it is a candidate."""
    reasons: list[str] = []
    if ticket.language != CANDIDATE_LANGUAGE:
        reasons.append(REASON_LANGUAGE)
    if ticket.ticket_type not in CANDIDATE_TICKET_TYPES:
        reasons.append(REASON_TICKET_TYPE)
    if ticket.queue not in CANDIDATE_QUEUES:
        reasons.append(REASON_QUEUE)
    return reasons


def filter_candidates(tickets: Iterable[Ticket]) -> FilterResult:
    result = FilterResult()
    for ticket in tickets:
        reasons = rejection_reasons(ticket)
        if reasons:
            result.rejected.append(
                {"stage": "filtering", "reasons": reasons, **asdict(ticket)}
            )
        else:
            result.candidates.append(ticket)

    logger.info(
        "Filtering: %d candidates, %d rejected",
        len(result.candidates),
        len(result.rejected),
    )
    return result
