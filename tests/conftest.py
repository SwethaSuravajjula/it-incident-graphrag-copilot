"""Shared test fixtures. Tickets here are small synthetic examples, not real data."""

import csv
from pathlib import Path

import pytest

COLUMNS = [
    "subject", "body", "answer", "type", "queue", "priority", "language", "version",
    "tag_1", "tag_2", "tag_3", "tag_4", "tag_5", "tag_6", "tag_7", "tag_8",
]


def make_row(**overrides: str) -> dict[str, str]:
    """A raw CSV row that passes cleaning and filtering, with fields overridden."""
    row = {column: "" for column in COLUMNS}
    row.update(
        subject="Printer offline",
        body="The printer on floor 2 is offline.",
        answer="Please restart the printer.",
        type="Incident",
        queue="Technical Support",
        priority="high",
        language="en",
        version="400",
        tag_1="Hardware",
    )
    row.update(overrides)
    return row


@pytest.fixture
def raw_rows() -> list[dict[str, str]]:
    """One row per behaviour we care about; comments give the expected outcome."""
    return [
        # 0: candidate. <br> becomes a newline.
        make_row(body="The printer on floor 2 is offline.<br><br>Please help."),
        # 1: candidate. Missing subject and answer must stay missing.
        make_row(subject="", body="VPN drops every hour.", answer="", type="Problem", queue="IT Support"),
        # 2: filtered out: language only.
        make_row(subject="Drucker", body="Der Drucker ist offline.", language="de"),
        # 3: filtered out: ticket type only.
        make_row(subject="New laptop", body="I would like a new laptop.", type="Request"),
        # 4: filtered out: queue only.
        make_row(subject="Invoice", body="My invoice is wrong.", queue="Billing and Payments"),
        # 5: filtered out: all three reasons.
        make_row(subject="Rechnung", body="Falsche Rechnung.", type="Change", queue="Human Resources", language="de"),
        # 6: rejected by cleaning: empty body (only a <br>).
        make_row(subject="Empty", body="<br>"),
        # 7: rejected by cleaning: same subject + body as row 0 apart from whitespace.
        make_row(body="  The printer on floor 2 is offline.<br><br>Please   help.  "),
        # 8: candidate. Tag blanks/duplicates dropped, <name> token kept, whitespace trimmed.
        make_row(
            subject=" Site down ", body="Hello <name>, the site is down. ", queue="Service Outages and Maintenance",
            type="Problem", tag_1="Outage", tag_2="", tag_3="Outage", tag_4=" Web ", priority="LOW",
        ),
    ]


@pytest.fixture
def raw_csv(tmp_path: Path, raw_rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "raw" / "tickets.csv"
    path.parent.mkdir()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(raw_rows)
    return path
