"""Run the first semantic extraction experiment on a reproducible sample of candidate tickets.

Usage:
    python -m src.extraction.run_sample [--size N] [--seed S] [--model ID]

Input:
    data/processed/02_candidates/candidate_tickets.jsonl

Outputs (under data/processed/):
    extracted_tickets_sample.jsonl           validated extractions
    extracted_tickets_sample_failures.jsonl  tickets that failed, with reason and raw output
    extracted_tickets_sample_manifest.json   sample ids, counts, model, prompt version, usage
"""

import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import EXTRACTION_MODEL, PROCESSED_DATA_DIR
from src.extraction.extractor import MAX_OUTPUT_TOKENS, STAGE_API_ERROR, extract_ticket
from src.extraction.groq_provider import make_provider
from src.extraction.llm import FatalAPIError, LLMProvider
from src.extraction.prompt import PROMPT_VERSION
from src.extraction.sampling import DEFAULT_SAMPLE_SIZE, DEFAULT_SEED, sample_tickets, ticket_ids
from src.extraction.usage import TokenUsage, estimate_cost_usd
from src.ingestion.io import read_jsonl, write_json
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)

CANDIDATES_PATH = PROCESSED_DATA_DIR / "02_candidates" / "candidate_tickets.jsonl"
RESULTS_NAME = "extracted_tickets_sample.jsonl"
FAILURES_NAME = "extracted_tickets_sample_failures.jsonl"
MANIFEST_NAME = "extracted_tickets_sample_manifest.json"

# Stop early when the API keeps failing (daily quota exhausted, outage) instead of
# spending minutes retrying every remaining ticket.
MAX_CONSECUTIVE_API_ERRORS = 5


class RunAborted(Exception):
    """The run could not start (no credentials, bad key, unknown model). No files were touched."""


def _append(handle: Any, record: dict[str, Any]) -> None:
    """Write one JSONL line and flush, so a crash mid-run keeps everything finished so far."""
    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    handle.flush()


def run(
    input_path: Path = CANDIDATES_PATH,
    output_dir: Path = PROCESSED_DATA_DIR,
    size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
    model: str = EXTRACTION_MODEL,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Extract a sample, write results/failures/manifest, and return the manifest."""
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    candidates = list(read_jsonl(input_path))
    sample = sample_tickets(candidates, size=size, seed=seed)
    logger.info("sampled %d of %d candidate tickets (seed=%d)", len(sample), len(candidates), seed)

    # Preflight before opening any output file, so a failed start never overwrites earlier results.
    try:
        provider = provider or make_provider()
        provider.check_access(model)
    except FatalAPIError as error:
        raise RunAborted(f"{error} (model: {model})") from error

    usage = TokenUsage()
    technical = non_technical = failed = consecutive_api_errors = 0
    failures_by_stage: Counter[str] = Counter()
    aborted: str | None = None

    output_dir.mkdir(parents=True, exist_ok=True)
    with (
        (output_dir / RESULTS_NAME).open("w", encoding="utf-8") as results,
        (output_dir / FAILURES_NAME).open("w", encoding="utf-8") as failures,
    ):
        for position, ticket in enumerate(sample, start=1):
            try:
                outcome = extract_ticket(provider, ticket, model=model, usage=usage)
            except FatalAPIError as error:
                aborted = str(error)
                logger.error("run aborted at ticket %d/%d: %s", position, len(sample), aborted)
                break
            if outcome.record is not None:
                consecutive_api_errors = 0
                _append(results, outcome.record)
                if outcome.record["is_technical_incident"]:
                    technical += 1
                else:
                    non_technical += 1
            else:
                _append(failures, outcome.failure)
                failed += 1
                failures_by_stage[outcome.failure["stage"]] += 1
                consecutive_api_errors = consecutive_api_errors + 1 if outcome.failure["stage"] == STAGE_API_ERROR else 0
                if consecutive_api_errors >= MAX_CONSECUTIVE_API_ERRORS:
                    aborted = f"{consecutive_api_errors} consecutive API errors (quota or outage?); see failures file"
                    logger.error("run aborted at ticket %d/%d: %s", position, len(sample), aborted)
                    break
            logger.info("%d/%d done", position, len(sample))

    manifest = {
        "stage": "extraction_sample",
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": input_path.name,
        "sample": {"size": size, "seed": seed, "ticket_ids": ticket_ids(sample)},
        "provider": provider.name,
        "model": model,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "prompt_version": PROMPT_VERSION,
        "tickets_attempted": technical + non_technical + failed,
        "extracted": technical + non_technical,
        "technical": technical,
        "non_technical": non_technical,
        "failed": failed,
        "failures_by_stage": dict(sorted(failures_by_stage.items())),
        "aborted": aborted,
        "usage": usage.to_dict(),
        "estimated_cost_usd": estimate_cost_usd(model, usage),
    }
    write_json(output_dir / MANIFEST_NAME, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=CANDIDATES_PATH)
    parser.add_argument("--out", type=Path, default=PROCESSED_DATA_DIR)
    parser.add_argument("--size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--model", default=EXTRACTION_MODEL)
    args = parser.parse_args()

    setup_logging()
    try:
        manifest = run(args.input, args.out, args.size, args.seed, args.model)
    except RunAborted as error:
        raise SystemExit(f"Run aborted before starting (no files written): {error}")
    print(json.dumps({k: v for k, v in manifest.items() if k != "sample"}, indent=2))
    if manifest["aborted"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
