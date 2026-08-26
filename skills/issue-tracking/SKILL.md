---
name: issue-tracking
description: Guidelines for creating, updating, closing, or replying to issues/tasks in any issue tracker (e.g., GitHub, Jira, Linear)
---
# Issue authoring

## Issue creation

You MUST avoid creating a duplicate. Search the tracker for potential duplicates, covering both open and closed issues. If a match exists, you SHOULD add any new and relevant information as a comment; if the match is closed, you SHOULD reopen it or file a follow-up.

You MUST observe the ghost-writing skill with semi-formal tone when creating an issue.

When filing bug reports or feature requests, you MUST use the language that a power user of the product would use, although you MAY include relevant environmental and/or implementation details at the bottom of the description if known.

### Issue title

A single succinct sentence explaining the issue (if a bug report) or the desired outcome (if a feature request or task).

### Issue description

You MUST use the following template unless the user or the issue tracker instructs you to use a different one:

Bug report:

```markdown
# Overview

(One or two succinct sentences that summarise the issue, who's affected, and the impact.)

# Current behaviour

(What happens today, with the steps that reproduce it. Screenshots SHOULD be included if relevant and readily available.)

# Expected behaviour

(What should happen instead, and how to tell when it's fixed.)

# Implementation details

(Optional section; skip unless details are already known. Where in the code the bug is, and when it was introduced. No solution should be prescribed, but suggestions can be made.)
```

Feature request:

```markdown
# Overview

(One or two succinct sentences that summarise a user's problem, and their proposed solution.)

# Problem

(The user problem that the product does not yet address.)

# Proposed solution

(Optional section; what the ideal solution looks like from the user's perspective.)

# Alternatives considered

(Optional section; skip if no solution is proposed. One or more alternatives, along with their pros and cons. Alternatives that do not require product changes SHOULD ideally be included.)

# Architectural and/or implementation considerations

(Optional section; skip unless user requests it. Any relevant suggestions or considerations in the context of the systems architecture, software architecture, or code implementation.)
```

Any references to specific parts of the code MUST be linkified with GitHub permalinks or equivalent.

## Issue update

You MUST observe the issue's pre-existing language, tone, and structure (especially if the author is different from the current user), unless the user says otherwise.

You MUST ensure that the description reflects our current understanding of the issue or plans. You MUST NOT append corrections.

## Issue resolution

- Say what changed and how it was verified, linking to the change that resolved it.
- Close as "not planned", or the tracker's equivalent, when the issue will not be acted upon, and give the reason.

# Comment authoring

Every comment you write or edit MUST observe the ghost-writing skill with informal tone.

# User sign-off

You MUST obtain user sign-off before performing any write operation on the issue tracker on their behalf. Unless told not to, you MUST present the ghost-written content to the user for sign-off.
