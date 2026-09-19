# CLAUDE.md

## Project

This repository contains an AI engineering project called
"IT Incident Triage & Support Copilot".

The system will combine:

- NLP
- knowledge graphs
- semantic retrieval
- GraphRAG
- LLM generation
- FastAPI
- Docker
- Google Cloud Platform

## Development Philosophy

The user is learning knowledge graphs, cloud engineering,
GraphRAG and production AI development while building this project.

Do not unnecessarily hide important architectural decisions.

Before making a major architectural change:

1. Explain what you intend to change.
2. Explain why it is necessary.
3. List the files that will be modified.
4. Keep changes modular and testable.

Do not implement large unrelated pieces of functionality at once.

## Knowledge Graph

The authoritative ontology is:

docs/ontology.md

Do not introduce new node types or relationship types unless
there is a clear reason.

If a new ontology concept is required, explain why before
modifying the ontology.

Never fabricate facts that are not supported by the ticket data.

In particular:

- do not invent root causes
- do not assume a support response resolved the incident
- distinguish possible causes from confirmed facts
- preserve missing information as missing

## Dataset

Raw data lives under:

data/raw/

Processed data lives under:

data/processed/

Do not commit raw or processed datasets to Git.

Do not modify the original raw dataset.

All transformations must create new processed outputs.

## Extraction

Structured extraction should eventually produce fields such as:

- ticket_id
- is_technical_incident
- systems
- symptoms
- issues
- possible_causes
- support_actions
- team
- priority
- tags

Support actions must use one of:

- request_information
- troubleshooting
- workaround
- status_update
- resolution
- general_response

## Code Quality

Use:

- typed Python where practical
- small modules
- clear function names
- environment variables for secrets
- meaningful logging
- unit tests for important transformations

Do not hardcode credentials.

Do not put API keys in source code.

## Workflow

Work incrementally.

Preferred workflow:

understand problem
-> implement small feature
-> test
-> inspect results
-> commit
-> continue

Do not generate the entire system in one step.