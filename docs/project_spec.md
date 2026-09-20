# IT Incident Triage & Support Copilot

## Goal

Build an AI-powered system that analyzes technical support incidents
and helps support engineers understand:

- what system is affected
- what symptoms are present
- what technical issue is being reported
- what possible causes are explicitly mentioned
- what support action was taken
- which team handles the incident
- which historical incidents are related

The final system will combine semantic retrieval and knowledge-graph
retrieval using a GraphRAG-style architecture.

## Dataset

Multilingual customer-support ticket dataset.

For version 1:

- use English tickets
- focus on Incident and Problem ticket types
- focus primarily on technical support-related queues

The raw dataset must not be committed to Git.

## Initial Architecture

Raw Dataset
    |
    v
Data Cleaning
    |
    v
Technical Incident Filtering
    |
    v
Structured Entity Extraction
    |
    v
Ontology Validation
    |
    v
Knowledge Graph
    |
    +--------------------+
    |                    |
    v                    v
Graph Retrieval      Vector Retrieval
    |                    |
    +---------+----------+
              |
              v
             LLM
              |
              v
     Support Copilot Response

## Deployment

The final application will be:

- Python
- FastAPI
- Docker
- deployed on Google Cloud Platform

## Version 1 Decisions

Source dataset: `data/raw/aa_dataset-tickets-multi-lang-5-2-50-version.csv`
(28,587 rows). No other dataset file is used in v1.

Candidate filtering (deterministic, metadata only):

- language = en
- type in Incident, Problem
- queue in Technical Support, IT Support,
  Service Outages and Maintenance, Product Support

This produces candidate tickets only. Whether a candidate is really a
technical incident (`is_technical_incident`) is decided later, semantically,
during extraction. It is pipeline metadata and never enters the graph.

Ticket identity: `ticket_id` is the SHA-256 of the normalized raw subject + body
(Unicode NFC, whitespace collapsed, trimmed; a newline separates the two fields).
IDs are generated before cleaning and never depend on row order.

Method: deterministic rules for structured fields and filtering; an LLM for
semantic technical classification and entity extraction. Extraction starts
with 50 candidate tickets.

Stage outputs are written under `data/processed/`, one folder per stage, and
every stage also writes its rejected records with the reasons.

Out of scope for now: GraphRAG, retrieval, API, Neo4j, GCP.

Processed ticket datasets use JSONL for easy inspection and later extraction, with `all_tags` combining `tag_1` through
`tag_8` in source order, excluding blank and exact duplicate tags. Rejections use
JSONL to retain heterogeneous diagnostic records and original rows. Empty bodies
and later duplicate IDs are explicitly rejected, never silently dropped.
