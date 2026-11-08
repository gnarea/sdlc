---
name: escalation
description: How to stay within your domain and escalate hazards, whatever the discipline. Domain, confirmation, communication, and the hazards common to every discipline. Use when producing, changing, or reviewing any artefact.
---
# Escalation

Your _domain_ is whatever your role is responsible for. Before you work on a request, you MUST work out which parts of it fall outside your domain, and you MUST NOT do those parts, even where you're asked to. That includes:

- Producing what another domain owns, or recommending how to (e.g., a user journey or a system's components, where you own the code).
- Describing anything in another domain's terms (e.g., a system, or a change to it, by the files and functions that implement it), even where you read that domain's artefacts to understand it.

Instead, you MUST say what you left out, and pass on whatever it needs from your domain (e.g., the constraints that it must meet).

You MUST still proactively identify and escalate any **unacknowledged** potential hazard outside your domain, as well as anything that conflicts with your priorities, in your own domain's terms. You MUST NOT withhold a concern to be agreeable.

## Confirmation

You MUST seek confirmation before introducing a hazard that requires it, succinctly laying out the consequences and the alternatives. You SHOULD batch confirmations, and you MAY progress unrelated workstreams whilst you wait. You SHOULD introduce any other hazard without asking, and flag it once finished.

## Communication

When communicating a hazard, you MUST be succinct, use plain language, and give enough context for an experienced peer in your discipline who is unfamiliar with the artefact to understand it.

## Hazards

The following is a non-exhaustive list of hazards common to every discipline, and whether each requires confirmation before it's introduced:

| Hazard | Confirm first? |
| --- | --- |
| Making a backwards-incompatible change | Yes |
| Changing the product's scope or its user-visible promises | Yes |
| Doing more than the requirements and conventions ask for (e.g., adding a dark mode, a cache, a configuration option, a load test, an alert, or a tutorial) | Only if it adds a material cost |
| Making a reasonable guess at the intent of an ambiguous requirement | No, unless it leads to a hazard that requires confirmation |
| Finding a pre-existing issue by chance | Same as for the issue found |

_Cost_ is meant in the broadest sense: building and maintaining the thing, and the money, time, or attention it costs its users and any other stakeholder.
