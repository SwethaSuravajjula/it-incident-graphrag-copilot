"""Project paths and environment-based settings. No secrets live in code."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

# The single source dataset for v1 (see docs/project_spec.md).
V1_SOURCE_DATASET = RAW_DATA_DIR / "aa_dataset-tickets-multi-lang-5-2-50-version.csv"

load_dotenv(PROJECT_ROOT / ".env")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# LLM used for semantic extraction (Groq API). The SDK reads GROQ_API_KEY from the environment.
# Schema-constrained ("strict") JSON output is only supported on some Groq models, e.g. openai/gpt-oss-*.
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "openai/gpt-oss-120b")
