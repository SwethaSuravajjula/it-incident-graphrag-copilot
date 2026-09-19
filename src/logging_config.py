"""Logging setup shared by all modules."""

import logging

from src.config import LOG_LEVEL


def setup_logging(level: str = LOG_LEVEL) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
