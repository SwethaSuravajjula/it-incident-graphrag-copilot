"""Run raw data -> cleaning -> candidate filtering and save inspectable outputs.

Usage:
    python -m src.ingestion.pipeline [--raw PATH] [--out DIR]

Outputs (under data/processed/ by default):
    01_cleaned/cleaned_tickets.jsonl       all tickets that survived cleaning
    01_cleaned/rejected_cleaning.jsonl     rows dropped by cleaning, with reasons
    01_cleaned/manifest.json
    02_candidates/candidate_tickets.jsonl  tickets passing the metadata filter
    02_candidates/rejected_filtering.jsonl tickets failing it, with all reasons
    02_candidates/manifest.json
"""

import argparse
import logging
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import PROCESSED_DATA_DIR, V1_SOURCE_DATASET
from src.ingestion.clean import clean_tickets
from src.ingestion.filter import (
    CANDIDATE_LANGUAGE,
    CANDIDATE_QUEUES,
    CANDIDATE_TICKET_TYPES,
    filter_candidates,
)
from src.ingestion.io import file_sha256, write_json, write_jsonl
from src.ingestion.load import read_raw_rows
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)

CLEANED_DIR = "01_cleaned"
CANDIDATES_DIR = "02_candidates"


def _reason_counts(rejected: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in rejected:
        counts.update(record["reasons"])
    return dict(sorted(counts.items()))


def run(raw_path: Path = V1_SOURCE_DATASET, output_dir: Path = PROCESSED_DATA_DIR) -> dict[str, Any]:
    """Run both stages, write all outputs, and return the summary counts."""
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    source = {"file": raw_path.name, "sha256": file_sha256(raw_path)}

    rows = read_raw_rows(raw_path)
    cleaning = clean_tickets(rows)
    filtering = filter_candidates(cleaning.tickets)

    cleaned_dir = output_dir / CLEANED_DIR
    write_jsonl(cleaned_dir / "cleaned_tickets.jsonl", (asdict(t) for t in cleaning.tickets))
    write_jsonl(cleaned_dir / "rejected_cleaning.jsonl", cleaning.rejected)
    cleaning_manifest = {
        "stage": "cleaning",
        "generated_at": generated_at,
        "source": source,
        "rows_read": len(rows),
        "tickets_kept": len(cleaning.tickets),
        "rows_rejected": len(cleaning.rejected),
        "rejected_by_reason": _reason_counts(cleaning.rejected),
    }
    write_json(cleaned_dir / "manifest.json", cleaning_manifest)

    candidates_dir = output_dir / CANDIDATES_DIR
    write_jsonl(candidates_dir / "candidate_tickets.jsonl", (asdict(t) for t in filtering.candidates))
    write_jsonl(candidates_dir / "rejected_filtering.jsonl", filtering.rejected)
    filtering_manifest = {
        "stage": "candidate_filtering",
        "generated_at": generated_at,
        "source": source,
        "filter": {
            "language": CANDIDATE_LANGUAGE,
            "ticket_types": sorted(CANDIDATE_TICKET_TYPES),
            "queues": sorted(CANDIDATE_QUEUES),
        },
        "tickets_in": len(cleaning.tickets),
        "candidates": len(filtering.candidates),
        "rejected": len(filtering.rejected),
        # A ticket can fail several filters, so these can add up to more than "rejected".
        "rejected_by_reason": _reason_counts(filtering.rejected),
        "candidates_by_queue": dict(sorted(Counter(t.queue for t in filtering.candidates).items())),
        "candidates_by_ticket_type": dict(sorted(Counter(t.ticket_type for t in filtering.candidates).items())),
    }
    write_json(candidates_dir / "manifest.json", filtering_manifest)

    return {"cleaning": cleaning_manifest, "candidate_filtering": filtering_manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", type=Path, default=V1_SOURCE_DATASET, help="raw CSV to read")
    parser.add_argument("--out", type=Path, default=PROCESSED_DATA_DIR, help="output directory")
    args = parser.parse_args()

    setup_logging()
    summary = run(args.raw, args.out)
    logger.info("Done: %d candidate tickets", summary["candidate_filtering"]["candidates"])


if __name__ == "__main__":
    main()
