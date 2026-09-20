"""Output-schema validation. Records here are synthetic examples, not real data."""

import copy

from src.extraction.schema import (
    MODEL_FIELDS,
    MODEL_OUTPUT_SCHEMA,
    SUPPORT_ACTION_TYPES,
    validate_extraction,
)

TICKET_ID = "a" * 64


def valid_record() -> dict:
    return {
        "ticket_id": TICKET_ID,
        "is_technical_incident": True,
        "systems": ["VPN client"],
        "symptoms": ["connection drops every hour"],
        "issues": ["network connectivity failure"],
        "possible_causes": [],
        "support_actions": [
            {"action": "Asks the customer to restart the client", "action_type": "troubleshooting"},
        ],
    }


def errors_for(record, has_answer: bool = True) -> list[str]:
    return validate_extraction(record, expected_ticket_id=TICKET_ID, has_answer=has_answer)


def test_valid_record_has_no_errors() -> None:
    assert errors_for(valid_record()) == []


def test_empty_lists_are_valid() -> None:
    record = valid_record()
    for field in ("systems", "symptoms", "issues", "possible_causes", "support_actions"):
        record[field] = []
    assert errors_for(record) == []


def test_every_ontology_action_type_is_accepted() -> None:
    for action_type in SUPPORT_ACTION_TYPES:
        record = valid_record()
        record["support_actions"] = [{"action": "x", "action_type": action_type}]
        assert errors_for(record) == []


def test_unknown_action_type_is_rejected() -> None:
    record = valid_record()
    record["support_actions"][0]["action_type"] = "escalation"
    assert any("action_type" in error for error in errors_for(record))


def test_missing_and_unexpected_fields_are_reported() -> None:
    record = valid_record()
    del record["symptoms"]
    record["team"] = "IT Support"
    errors = errors_for(record)
    assert any("missing fields ['symptoms']" in error for error in errors)
    assert any("unexpected fields ['team']" in error for error in errors)


def test_ticket_id_must_match_source_ticket() -> None:
    record = valid_record()
    record["ticket_id"] = "b" * 64
    assert any("ticket_id" in error for error in errors_for(record))


def test_is_technical_incident_must_be_a_boolean() -> None:
    record = valid_record()
    record["is_technical_incident"] = "yes"
    assert any("is_technical_incident" in error for error in errors_for(record))


def test_list_fields_must_hold_non_blank_strings() -> None:
    record = valid_record()
    record["systems"] = ["ok", "  ", 3]
    errors = errors_for(record)
    assert any("systems[1]: blank" in error for error in errors)
    assert any("systems[2]" in error for error in errors)


def test_string_instead_of_list_is_rejected() -> None:
    record = valid_record()
    record["possible_causes"] = "a bad cable"
    assert any("possible_causes: expected a list" in error for error in errors_for(record))


def test_support_action_shape_is_checked() -> None:
    record = valid_record()
    record["support_actions"] = ["restart", {"action": "", "action_type": "troubleshooting", "extra": 1}]
    errors = errors_for(record)
    assert any("support_actions[0]: expected an object" in error for error in errors)
    assert any("support_actions[1]: unexpected keys" in error for error in errors)
    assert any("support_actions[1].action" in error for error in errors)


def test_support_actions_without_an_answer_are_rejected() -> None:
    assert any("no support answer" in error for error in errors_for(valid_record(), has_answer=False))
    record = copy.deepcopy(valid_record())
    record["support_actions"] = []
    assert errors_for(record, has_answer=False) == []


def test_non_object_record_is_rejected() -> None:
    assert errors_for(["not", "an", "object"]) == ["record: expected an object, got list"]


def test_api_schema_and_local_validation_agree_on_fields() -> None:
    assert set(MODEL_OUTPUT_SCHEMA["properties"]) == set(MODEL_FIELDS)
    assert set(MODEL_OUTPUT_SCHEMA["required"]) == set(MODEL_FIELDS)
    item = MODEL_OUTPUT_SCHEMA["properties"]["support_actions"]["items"]
    assert item["properties"]["action_type"]["enum"] == list(SUPPORT_ACTION_TYPES)
