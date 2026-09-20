# IT Incident Triage & Support Copilot

Combines NLP, a knowledge graph, semantic retrieval, GraphRAG and LLM generation
to triage IT support tickets. See [CLAUDE.md](CLAUDE.md) for project rules and
[docs/ontology.md](docs/ontology.md) for the graph ontology.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pytest
```

## Layout

| Path | Purpose |
| --- | --- |
| `src/ingestion/` | Load and clean raw tickets |
| `src/extraction/` | Structured extraction from tickets |
| `src/graph/` | Knowledge graph construction |
| `src/retrieval/` | Semantic retrieval and GraphRAG |
| `src/api/` | FastAPI service |
| `data/raw/`, `data/processed/` | Datasets (git-ignored, never modify raw) |
| `docs/` | Ontology and project spec |

## Run the v1 ingestion slice

Place `aa_dataset-tickets-multi-lang-5-2-50-version.csv` in `data/raw/`, then run:

```bash
python -m src.ingestion.pipeline
```

Optional arguments: `--raw PATH --out DIR`. Defaults write to `data/processed/`.
Cleaned tickets and metadata-filtered candidates are saved as JSONL in
`01_cleaned/` and `02_candidates/`, with an `all_tags` JSON array assembled
from the source's `tag_1` through `tag_8`. Missing values remain null.
Each stage also writes a JSON manifest and JSONL rejections with reasons; JSONL
supports the different diagnostic structures, including original raw records.
Empty bodies and duplicate IDs are recorded as cleaning rejections (first
occurrence wins). No semantic classification or extraction runs in this slice.

JSONL keeps each ticket readable as one JSON object per line for inspection and
later extraction requests, without a Parquet dependency. Stage manifests remain JSON.
