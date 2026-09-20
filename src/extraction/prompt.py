"""Prompt for the semantic extraction experiment (docs/ontology.md is the authority)."""

from collections.abc import Mapping
from typing import Any

# Recorded in the run manifest so results can be tied to the prompt that produced them.
PROMPT_VERSION = "v1"

MISSING = "(missing)"

SYSTEM_PROMPT = """\
You extract structured facts from one IT support ticket for a knowledge graph. \
You are given the customer's SUBJECT and BODY, and the support agent's ANSWER. \
Report only what the text supports. Never add facts, causes or actions from general knowledge. \
Respond with a single JSON object.

Fields to return:

is_technical_incident (boolean)
  true only if the customer reports a genuine technical problem (something broken, failing, \
unavailable, erroring or misbehaving in software, hardware, network or a service) that a technical \
support engineer would triage.
  false for business, marketing, sales, billing, account-administration or general inquiries, feature \
or information requests, and anything else that is not genuinely a technical problem, even if it \
mentions a product or uses technical vocabulary.

systems (list of strings)
  Software, services, platforms, infrastructure components or devices that the ticket says are \
affected. Use the ticket's own names.

symptoms (list of strings)
  What the user observes going wrong (for example "cannot log in", "page returns an error", \
"sync stops after a few minutes"). Short phrases, one symptom each.

issues (list of strings)
  The broader technical issue category being reported (for example "service outage", \
"authentication failure", "data synchronization failure"). Short noun phrases.

possible_causes (list of strings)
  A cause ONLY when the ticket or the answer explicitly states it, or explicitly presents it as \
possible ("may be caused by", "could be due to", "we suspect"). Never infer a cause from the symptoms, \
and never propose a likely cause yourself. If the text only says something is broken, or that the \
team is "investigating", there is no cause: return an empty list.
  Keep the text's own uncertainty in the string: write "possibly a corrupted configuration file", \
not "corrupted configuration file", when the text hedges.

support_actions (list of objects with "action" and "action_type")
  One entry per distinct action the support agent's ANSWER takes or recommends. The customer's \
requests are not support actions. If the answer is "(missing)", return an empty list.
  "action" is a short, faithful paraphrase of what the answer says. Do not add steps it does not contain.
  "action_type" is exactly one of:
    request_information  asks the customer for more details, logs, screenshots or confirmation
    troubleshooting      diagnostic or repair steps the customer is asked to try, or that the team \
says it is carrying out (restart, clear cache, check settings, investigate)
    workaround           a temporary alternative that avoids the problem without fixing it
    status_update        reports the current state, progress or expected timing
    resolution           states that the problem HAS BEEN fixed or gives the definitive fix. \
Use it only when the answer says so. Promising to look into it, or a suggestion to try something, \
is not a resolution.
    general_response     acknowledgement, apology, thanks, closing or generic reassurance with no \
concrete technical content

General rules:
- Missing information stays missing: use an empty list rather than guessing.
- A support answer is not evidence that the incident was resolved. Do not assume it.
- Text such as <name> or <acc_num> is an anonymization placeholder, not a system or an error.
- Do not repeat the same item twice in a list.
- Write in English, in the wording of the ticket where possible.
"""


def build_user_message(ticket: Mapping[str, Any]) -> str:
    """Render the text fields of a candidate ticket. Missing fields are marked, not omitted.

    Metadata (queue, priority, tags) is deliberately left out: it is attached deterministically
    later, and tags could bias the model toward causes the text never mentions.
    """
    subject = ticket.get("subject") or MISSING
    answer = ticket.get("answer") or MISSING
    return f"SUBJECT:\n{subject}\n\nBODY:\n{ticket['body']}\n\nANSWER:\n{answer}"
