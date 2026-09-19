import unicodedata

import pytest

from src.ingestion.text import clean_text, make_ticket_id, normalize_for_id


@pytest.mark.parametrize("br", ["<br>", "<br/>", "<br />", "</br>", "<BR>"])
def test_clean_text_turns_br_variants_into_newlines(br: str):
    assert clean_text(f"Line one{br}Line two") == "Line one\nLine two"


def test_clean_text_turns_literal_backslash_n_into_newlines():
    assert clean_text(r"Dear Team,\n\nMy VPN fails.\r\nThanks") == "Dear Team,\n\nMy VPN fails.\nThanks"


def test_clean_text_unescapes_quotes():
    assert clean_text(r'\"<name>\" reported it') == '"<name>" reported it'


def test_ticket_id_is_unaffected_by_literal_backslash_n_handling():
    # IDs hash the raw text, so cleaning-rule changes never move them.
    assert make_ticket_id("s", r"a\nb") != make_ticket_id("s", "a\nb")


def test_clean_text_normalizes_whitespace_but_keeps_paragraphs():
    assert clean_text("  a   b \r\n\r\n\r\n\r\n c\t d  ") == "a b\n\nc d"


def test_clean_text_keeps_anonymization_tokens():
    assert clean_text("Hi <name>, call <tel_num>") == "Hi <name>, call <tel_num>"


@pytest.mark.parametrize("value", [None, "", "   ", "<br>", "\n\t "])
def test_clean_text_returns_none_when_nothing_is_left(value):
    assert clean_text(value) is None


def test_normalize_for_id_collapses_whitespace_and_unicode_forms():
    composed = "café"
    decomposed = unicodedata.normalize("NFD", composed)
    assert normalize_for_id(f"  {decomposed} \n\n bar ") == "café bar"


def test_ticket_id_is_pinned_sha256_of_normalized_subject_and_body():
    # If this fails, the ID scheme changed and every stored ticket_id is invalidated.
    ticket_id = make_ticket_id("Printer offline", "The printer on floor 2 is offline.")
    assert ticket_id == "3fe82bef2cc7f8b8b61dc5b42a71eff7891cc3f816e7c587a5269dfb9a6bb1bf"


def test_ticket_id_ignores_whitespace_differences():
    a = make_ticket_id("Printer  offline", "Line one\r\nLine two")
    b = make_ticket_id(" Printer offline ", "Line one Line two ")
    assert a == b


def test_ticket_id_treats_missing_subject_as_empty_and_is_case_sensitive():
    assert make_ticket_id(None, "body") == make_ticket_id("", "body")
    assert make_ticket_id("A", "body") != make_ticket_id("a", "body")


def test_ticket_id_does_not_confuse_subject_and_body_boundaries():
    assert make_ticket_id("ab", "c") != make_ticket_id("a", "bc")
