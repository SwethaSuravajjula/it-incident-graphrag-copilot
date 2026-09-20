"""Record types passed between ingestion stages."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    """A cleaned ticket. Missing values stay None; nothing is inferred."""

    ticket_id: str
    # 0-based data-row position in the raw CSV. Provenance only, never identity.
    source_row: int
    subject: str | None
    body: str
    answer: str | None
    ticket_type: str | None
    queue: str | None
    priority: str | None
    language: str | None
    all_tags: tuple[str, ...]
    # Raw `version` column. Meaning not documented in the source; kept as provenance.
    source_version: str | None
