"""Read the raw ticket CSV. The raw file is only ever opened for reading."""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TAG_COLUMNS = tuple(f"tag_{i}" for i in range(1, 9))
REQUIRED_COLUMNS = (
    "subject",
    "body",
    "answer",
    "type",
    "queue",
    "priority",
    "language",
    *TAG_COLUMNS,
)


def read_raw_rows(path: Path) -> list[dict[str, str]]:
    """Read every row as strings. Empty cells stay as empty strings."""
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name} is missing required columns: {missing}")
        rows = list(reader)
    logger.info("Read %d raw rows from %s", len(rows), path.name)
    return rows
