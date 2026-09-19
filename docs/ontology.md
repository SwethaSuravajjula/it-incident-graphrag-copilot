# Knowledge Graph Ontology v1

## Node Types

### Incident
A technical support incident or problem.

### System
Software, service, platform, infrastructure component, or device
affected by an incident.

### Symptom
An observable problem experienced by the user.

### Issue
The broader technical issue category.

### Cause
A cause explicitly mentioned or presented as a possible cause.

### SupportAction
An action taken or recommended by the support agent.

### Team
The support queue responsible for the incident.

### Tag
Metadata attached to a ticket.


## Incident Properties

Properties stored on the Incident node (not separate nodes):

- ticket_id: stable SHA-256 hash of the normalized ticket subject + body
- ticket_type: the ticket type from the source data (v1: Incident or Problem)
- priority: the priority from the source data (low, medium, high)
- language: the ticket language code (v1: en)

A property that is missing in the source data stays missing.

`is_technical_incident` is pipeline metadata. It is not an Incident
property and not a node.


## Relationships

Incident -> AFFECTS -> System

Incident -> HAS_SYMPTOM -> Symptom

Incident -> HAS_ISSUE -> Issue

Incident -> POSSIBLE_CAUSE -> Cause

Incident -> HAS_SUPPORT_ACTION -> SupportAction

Incident -> ASSIGNED_TO -> Team

Incident -> HAS_TAG -> Tag


## Important Rules

- Do not invent a cause when one is not present.
- Distinguish possible causes from confirmed facts.
- Do not assume every support answer is a resolution.
- SupportAction may represent:
  - request_information
  - troubleshooting
  - workaround
  - status_update
  - resolution
  - general_response
- Missing information should remain missing rather than being inferred.