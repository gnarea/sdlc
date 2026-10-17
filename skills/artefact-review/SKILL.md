---
name: artefact-review
description: How to review an artefact that you didn't produce, such as a spec, a design, or a change.
---
# Artefact review

## Findings

You MUST check the artefact for findings of each of the following kinds, so that the review is comprehensive:

- Defect: the artefact fails a requirement or a convention.
- Unfit: the artefact meets its requirements, but doesn't solve the underlying problem, possibly because the requirements were wrong or ambiguous.
- Omission: the artefact lacks something that no requirement asks for, but that it needs, possibly because the requirement is missing from the brief.
- Untraced: the artefact has something that you can't trace to a requirement, possibly because the requirement is missing from the brief, or because you missed the connection.
- Disproportionate: the artefact has a requirement or mechanism whose cost outweighs what it delivers. _Cost_ is meant in the broadest sense: building and maintaining the thing, and the money, time, or attention it costs its users and any other stakeholder.

These kinds are simply for conducting the review, and need not be relayed in the report.

Each finding MUST state what it is and the consequence of shipping the artefact as it stands. It MUST NOT propose an alternative, unless it's disproportionate, in which case it MUST say what dropping or simplifying the requirement or mechanism would save, and what would be lost. A finding that predates the change under review SHOULD be acknowledged as pre-existing.

## Severity

Each finding MUST be graded by the worst consequence of shipping the artefact as it stands or, for a spec or a design, of building it as specified:

- High: the artefact MUST NOT be shipped until the finding is addressed. This includes, but isn't limited to, any case where the artefact can:
  - Lose or corrupt data, or duplicate it in a way that a user would notice.
  - Expose a secret or personal data.
  - Let someone do what they aren't authorised to (e.g., impersonate another party, get a change through without the required approval).
  - Break backwards compatibility with a system that depends on it.
  - Impose a material cost on a stakeholder.
- Medium: the artefact SHOULD NOT be shipped until the finding is addressed. This includes, but isn't limited to, any case where the behaviour is wrong, or where the finding is in something expensive to reverse once shipped (e.g., an identifier, a wire format, a schema).
- Low: the artefact MAY still be shipped despite the finding.

A disproportionate requirement or mechanism MUST NOT be reported where it's graded low.

## Report

Unless you're asked to use a different template or format, you MUST write the report using the [report template](assets/report.md), leaving out any section that has nothing in it.
