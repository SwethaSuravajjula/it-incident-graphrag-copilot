import json

from src.ingestion.io import file_sha256, read_jsonl
from src.ingestion.pipeline import CANDIDATES_DIR, CLEANED_DIR, run


def test_pipeline_writes_all_stage_outputs_with_consistent_counts(raw_csv, tmp_path):
    out = tmp_path / "processed"
    summary = run(raw_csv, out)

    cleaned = list(read_jsonl(out / CLEANED_DIR / "cleaned_tickets.jsonl"))
    cleaning_rejects = list(read_jsonl(out / CLEANED_DIR / "rejected_cleaning.jsonl"))
    candidates = list(read_jsonl(out / CANDIDATES_DIR / "candidate_tickets.jsonl"))
    filter_rejects = list(read_jsonl(out / CANDIDATES_DIR / "rejected_filtering.jsonl"))

    assert (len(cleaned), len(cleaning_rejects)) == (7, 2)
    assert (len(candidates), len(filter_rejects)) == (3, 4)
    # Nothing is silently lost: every row is either kept or rejected somewhere.
    assert len(cleaning_rejects) + len(filter_rejects) + len(candidates) == 9
    assert summary["candidate_filtering"]["candidates"] == 3


def test_candidate_jsonl_records_have_expected_fields(raw_csv, tmp_path):
    out = tmp_path / "processed"
    run(raw_csv, out)
    candidates = list(read_jsonl(out / CANDIDATES_DIR / "candidate_tickets.jsonl"))

    assert set(candidates[0]) == {
        "ticket_id", "source_row", "subject", "body", "answer", "ticket_type",
        "queue", "priority", "language", "all_tags", "source_version",
    }
    assert candidates[0]["all_tags"] == ["Hardware"]
    assert candidates[1]["subject"] is None  # missing stays missing
    assert len({c["ticket_id"] for c in candidates}) == len(candidates)


def test_manifests_record_source_filter_and_reason_counts(raw_csv, tmp_path):
    out = tmp_path / "processed"
    run(raw_csv, out)
    manifest = json.loads((out / CANDIDATES_DIR / "manifest.json").read_text())

    assert manifest["source"]["sha256"] == file_sha256(raw_csv)
    assert manifest["filter"]["language"] == "en"
    assert manifest["filter"]["ticket_types"] == ["Incident", "Problem"]
    assert manifest["rejected_by_reason"] == {
        "language_not_en": 2,
        "queue_not_candidate": 2,
        "ticket_type_not_incident_or_problem": 2,
    }
    cleaning = json.loads((out / CLEANED_DIR / "manifest.json").read_text())
    assert cleaning["rejected_by_reason"] == {"duplicate_ticket_id": 1, "empty_body": 1}


def test_pipeline_never_modifies_the_raw_file(raw_csv, tmp_path):
    before = file_sha256(raw_csv)
    run(raw_csv, tmp_path / "processed")
    assert file_sha256(raw_csv) == before


def test_pipeline_is_deterministic_apart_from_the_manifest_timestamp(raw_csv, tmp_path):
    run(raw_csv, tmp_path / "a")
    run(raw_csv, tmp_path / "b")
    name = "candidate_tickets.jsonl"
    assert (tmp_path / "a" / CANDIDATES_DIR / name).read_bytes() == (
        tmp_path / "b" / CANDIDATES_DIR / name
    ).read_bytes()


def test_empty_input_writes_empty_jsonl_outputs(raw_csv, tmp_path):
    # Keep the CSV headers but provide no data records.
    raw_csv.write_text(raw_csv.read_text().splitlines()[0] + "\n")
    summary = run(raw_csv, tmp_path / "processed")
    for folder, filename in [
        (CLEANED_DIR, "cleaned_tickets.jsonl"),
        (CLEANED_DIR, "rejected_cleaning.jsonl"),
        (CANDIDATES_DIR, "candidate_tickets.jsonl"),
        (CANDIDATES_DIR, "rejected_filtering.jsonl"),
    ]:
        path = tmp_path / "processed" / folder / filename
        assert path.read_bytes() == b""
        assert list(read_jsonl(path)) == []
    assert summary["candidate_filtering"]["candidates"] == 0


def test_priority_distribution_preserves_missing_values(raw_rows, tmp_path):
    import csv
    from tests.conftest import COLUMNS

    raw_rows[0]["priority"] = ""
    path = tmp_path / "tickets.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(raw_rows)
    summary = run(path, tmp_path / "processed")["candidate_filtering"]
    assert summary["candidates_by_priority"] == {"high": 1, "low": 1}
    assert summary["candidates_missing_priority"] == 1
    candidates = list(read_jsonl(tmp_path / "processed" / CANDIDATES_DIR / "candidate_tickets.jsonl"))
    assert candidates[0]["priority"] is None
