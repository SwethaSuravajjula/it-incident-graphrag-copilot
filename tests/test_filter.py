import pytest

from src.ingestion.clean import clean_tickets
from src.ingestion.filter import (
    CANDIDATE_QUEUES,
    REASON_LANGUAGE,
    REASON_QUEUE,
    REASON_TICKET_TYPE,
    filter_candidates,
    rejection_reasons,
)


def test_candidate_queues_are_the_agreed_four():
    assert CANDIDATE_QUEUES == {
        "Technical Support",
        "IT Support",
        "Service Outages and Maintenance",
        "Product Support",
    }


def test_filter_splits_candidates_from_rejected(raw_rows):
    tickets = clean_tickets(raw_rows).tickets
    result = filter_candidates(tickets)

    assert [t.source_row for t in result.candidates] == [0, 1, 8]
    assert {r["source_row"] for r in result.rejected} == {2, 3, 4, 5}


def test_each_filter_reports_its_own_reason(raw_rows):
    reasons = {
        r["source_row"]: r["reasons"]
        for r in filter_candidates(clean_tickets(raw_rows).tickets).rejected
    }
    assert reasons[2] == [REASON_LANGUAGE]
    assert reasons[3] == [REASON_TICKET_TYPE]
    assert reasons[4] == [REASON_QUEUE]
    assert reasons[5] == [REASON_LANGUAGE, REASON_TICKET_TYPE, REASON_QUEUE]


@pytest.mark.parametrize("queue", sorted(CANDIDATE_QUEUES))
@pytest.mark.parametrize("ticket_type", ["Incident", "Problem"])
def test_every_allowed_combination_is_a_candidate(raw_rows, queue, ticket_type):
    raw_rows[0]["queue"], raw_rows[0]["type"] = queue, ticket_type
    ticket = clean_tickets(raw_rows[:1]).tickets[0]
    assert rejection_reasons(ticket) == []


def test_missing_metadata_is_rejected_not_assumed(raw_rows):
    raw_rows[0].update(queue="", type="", language="")
    ticket = clean_tickets(raw_rows[:1]).tickets[0]
    assert rejection_reasons(ticket) == [REASON_LANGUAGE, REASON_TICKET_TYPE, REASON_QUEUE]


def test_filtering_does_not_mutate_the_tickets(raw_rows):
    tickets = clean_tickets(raw_rows).tickets
    before = list(tickets)
    filter_candidates(tickets)
    assert tickets == before
