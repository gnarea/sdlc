# Context engineering

The _context_ is everything that an agent has in front of it when it responds: its prompts, whatever it has read (e.g., files, tool results), and the history of the session.

## Tool loadout

Choose which tools and skills an agent is offered:

- Each agent SHOULD only be offered the tools and skills that its tasks need, and no two of them SHOULD overlap in purpose.
- Where the harness can load tool definitions on demand, it SHOULD do so once they'd take up a large part of the context.
- Tools and commands SHOULD return only what the agent needs for its next step, and SHOULD keep anything longer outside the context, where the agent can read it in part.

## Quarantine

Consider giving part of the work to another agent that starts with an empty context:

- Work SHOULD be delegated where it would fill the context with material that the rest of the work doesn't need (e.g., researching a large corpus).
- Work SHOULD also be delegated to a specialised agent where it calls for instructions, tools, or permissions that would conflict with the delegator's (e.g., the priorities of another discipline), or for a view that isn't anchored on the delegator's reasoning. Where it only calls for more instructions, the delegator SHOULD consider loading a skill instead, since one agent with skills often does better than several agents.
- Where the input is large, it SHOULD be divided between delegates, each owning one deliverable, and each delegate SHOULD be encouraged to divide its share in turn.
- Where missing something would be costly, the delegates' shares MAY overlap on purpose, so that one can pick up what another misses.
- Each delegate MUST trace every claim to its source (e.g., a file path, a URL, a quotation). Where delegates disagree, the combined result MUST say so, rather than pick one.
- A review SHOULD run in a fresh context that has the artefact and its requirements, but not the reasoning that produced it.

## Offloading

Consider keeping information outside the context (e.g., in a file, in an issue tracker), for the agent to read back when it needs it:

- A deliverable that outlives the session, or that someone else needs, MUST be written outside the context (e.g., to a file, as a comment on an issue), and passed on by reference.
- Exact details that later work needs (e.g., paths, identifiers, error messages) MUST be written down outside the context, rather than left to a summary of the history.
- Where the harness can start a fresh session, long-running work SHOULD be split into sessions bounded by time or tokens, each ending with notes. An agent that stops making progress SHOULD start afresh from its notes and its work, carrying over what failed and why, but not the attempts themselves.

## Pruning

Where the harness calls the model itself, and the model allows its history to be edited, old tool output SHOULD be dropped from the history by a fixed rule, and a summary written by a model SHOULD only be added where evals show that it does better.

## Summarisation

A summary that another agent or a person will act on MUST state the conclusions and the evidence behind them, leaving out how they were reached.

## Context persisted across sessions

- Unless told otherwise, an agent that builds or maintains a project MUST NOT decide for itself what to remember (e.g., Claude Code's auto memory, CodeRabbit's learnings), since it tends to apply a preference or a decision beyond the situation in which someone expressed it. Whatever must carry over MUST be written down on purpose instead, in files that a person reviews (e.g., `AGENTS.md`, `CLAUDE.md`, a rule scoped to some files), even where an agent drafts them.
- A product MAY still have agents that persist context automatically, since whether it does is a decision about the product, rather than about how it's built.
