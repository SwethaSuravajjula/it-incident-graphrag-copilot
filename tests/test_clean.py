from src.ingestion.clean import REASON_DUPLICATE_ID, REASON_EMPTY_BODY, clean_tickets
from src.ingestion.text import make_ticket_id


def test_clean_keeps_valid_rows_and_rejects_empty_body_and_duplicates(raw_rows):
    result = clean_tickets(raw_rows)

    assert [t.source_row for t in result.tickets] == [0, 1, 2, 3, 4, 5, 8]
    reasons = {r["source_row"]: r["reasons"] for r in result.rejected}
    assert reasons == {6: [REASON_EMPTY_BODY], 7: [REASON_DUPLICATE_ID]}


def test_duplicate_rejection_points_at_the_first_row(raw_rows):
    result = clean_tickets(raw_rows)
    duplicate = next(r for r in result.rejected if r["source_row"] == 7)
    assert duplicate["duplicate_of_source_row"] == 0
    assert duplicate["ticket_id"] == result.tickets[0].ticket_id


def test_rejected_empty_body_row_keeps_the_raw_row_for_inspection(raw_rows):
    result = clean_tickets(raw_rows)
    empty = next(r for r in result.rejected if r["source_row"] == 6)
    assert empty["raw"]["subject"] == "Empty"


def test_missing_subject_and_answer_stay_none(raw_rows):
    ticket = clean_tickets(raw_rows).tickets[1]
    assert ticket.subject is None
    assert ticket.answer is None


def test_text_is_cleaned_but_ticket_id_uses_raw_text(raw_rows):
    ticket = clean_tickets(raw_rows).tickets[0]
    assert ticket.body == "The printer on floor 2 is offline.\n\nPlease help."
    assert ticket.ticket_id == make_ticket_id(raw_rows[0]["subject"], raw_rows[0]["body"])


def test_tags_drop_blanks_and_duplicates_and_keep_order(raw_rows):
    ticket = next(t for t in clean_tickets(raw_rows).tickets if t.source_row == 8)
    assert ticket.tags == ("Outage", "Web")


def test_categorical_fields_are_trimmed_and_priority_language_lowercased(raw_rows):
    ticket = next(t for t in clean_tickets(raw_rows).tickets if t.source_row == 8)
    assert (ticket.priority, ticket.language) == ("low", "en")
    assert (ticket.ticket_type, ticket.queue) == ("Problem", "Service Outages and Maintenance")
    assert ticket.subject == "Site down"
    assert ticket.body == "Hello <name>, the site is down."


def test_empty_categorical_value_becomes_none_not_a_guess(raw_rows):
    raw_rows[0]["priority"] = "  "
    assert clean_tickets(raw_rows).tickets[0].priority is None


def test_source_version_is_kept_as_provenance(raw_rows):
    assert clean_tickets(raw_rows).tickets[0].source_version == "400"
