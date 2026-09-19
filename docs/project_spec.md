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