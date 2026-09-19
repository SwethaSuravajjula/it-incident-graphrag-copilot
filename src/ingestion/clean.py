"""Cleaning stage: raw rows -> Ticket records, plus rejected rows with reasons."""

import logging
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from src.ingestion.load import TAG_COLUMNS
from src.ingestion.schema import Ticket
from src.ingestion.text import clean_text, make_ticket_id

logger = logging.getLogger(__name__)

REASON_EMPTY_BODY = "empty_body"
REASON_DUPLICATE_ID = "duplicate_ticket_id"


@dataclass
class CleaningResult:
    tickets: list[Ticket] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)


def _clean_label(value: str | None) -> str | None:
    """Trim a categorical value; empty becomes None (missing stays missing)."""
    if value is None:
        return None
    return value.strip() or None


def _clean_tags(row: Mapping[str, str]) -> tuple[str, ...]:
    """Collect tag_1..tag_8, dropping blanks and exact duplicates, keeping order."""
    tags: list[str] = []
    for column in TAG_COLUMNS:
        tag = _clean_label(row.get(column))
        if tag is not None and tag not in tags:
            tags.append(tag)
    return tuple(tags)


def clean_tickets(rows: Iterable[Mapping[str, str]]) -> CleaningResult:
    """Clean raw rows.

    A row is rejected when its body is empty (nothing to analyze) or when its
    ticket_id was already produced by an earlier row (duplicate content).
    Missing subjects and answers are kept as None.
    """
    result = CleaningResult()
    first_row_by_id: dict[str, int] = {}

    for source_row, row in enumerate(rows):
        body = clean_text(row.get("body"))
        if body is None:
            result.rejected.append(
                {
                    "stage": "cleaning",
                    "reasons": [REASON_EMPTY_BODY],
                    "source_row": source_row,
                    "raw": dict(row),
                }
            )
            continue

        ticket_id = make_ticket_id(row.get("subject"), row.get("body"))
        priority = _clean_label(row.get("priority"))
        language = _clean_label(row.get("language"))
        ticket = Ticket(
            ticket_id=ticket_id,
            source_row=source_row,
            subject=clean_text(row.get("subject")),
            body=body,
            answer=clean_text(row.get("answer")),
            ticket_type=_clean_label(row.get("type")),
            queue=_clean_label(row.get("queue")),
            priority=priority.lower() if priority else None,
            language=language.lower() if language else None,
            tags=_clean_tags(row),
            source_version=_clean_label(row.get("version")),
        )

        if ticket_id in first_row_by_id:
            result.rejected.append(
                {
                    "stage": "cleaning",
                    "reasons": [REASON_DUPLICATE_ID],
                    "duplicate_of_source_row": first_row_by_id[ticket_id],
                    **asdict(ticket),
                }
            )
            continue

        first_row_by_id[ticket_id] = source_row
        result.tickets.append(ticket)

    logger.info(
        "Cleaning: %d kept, %d rejected", len(result.tickets), len(result.rejected)
    )
    return result
