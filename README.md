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
