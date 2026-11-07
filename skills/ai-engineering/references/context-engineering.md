# Context engineering

The _context_ is everything that an agent has in front of it when it responds: its prompts, whatever it has read (e.g., files, tool results), and the history of the session.

## Augmentation

_Context augmentation_ is giving an agent the information that its task needs (e.g., in the prompt, through a search index, in a skill).

- Text that loads at the start of every session (e.g., a system prompt, a project's instructions for agents such as `CLAUDE.md`) MUST be limited to what every task needs and the agent can't discover for itself (e.g., a convention that departs from the norm, the commands for common tasks), plus pointers to where the rest lives.
- A project's instructions for agents MUST be succinct (e.g., under 100 lines), and MUST NOT repeat the project's other documents.
- Whatever only some tasks need SHOULD be loaded when they need it (e.g., from a skill, a reference file, or a document that the prompt points to).
- The description of a skill or an agent MUST say what it covers and when to use it, in the terms that a matching request would use.
- A skill that applies to every task that an agent performs SHOULD be preloaded, rather than left for the agent to load when its description matches.

## Memory

_Memory_ is whatever an agent's context carries over from one session to the next.

- An agent that builds or maintains a project MUST NOT decide for itself what to remember (e.g., through Claude Code's auto memory, or CodeRabbit's learnings), since it tends to apply a preference or a decision beyond the situation in which someone expressed it. Whatever must carry over MUST be written down on purpose instead, in files that a person reviews (e.g., `AGENTS.md`, `CLAUDE.md`, a rule scoped to some files), even where an agent drafts them.
- A product MAY still offer memory that its own agents manage, since whether it does is a decision about the product, rather than about how it's built.

## Tool loadout

_Tool loadout_ is choosing which tools and skills an agent is offered.

- Each agent SHOULD only be offered the tools and skills that its tasks need, and no two of them SHOULD overlap in purpose.
- Where the harness can load tool definitions on demand, it SHOULD do so once they'd take up a large part of the context (e.g., over 10,000 tokens).
- Tools and commands SHOULD return only what the agent needs for its next step, and SHOULD write anything longer to a file that the agent can read in part.

## Quarantine

_Context quarantine_ is giving part of the work to another agent, which starts with an empty history (e.g., a subagent).

- Work SHOULD be delegated where it would fill the context with material that the rest of the work doesn't need (e.g., researching a large corpus).
- Where the input is large, it SHOULD be divided between delegates, each owning one deliverable, and each delegate SHOULD be encouraged to divide its share in turn.
- Where missing something would be costly, the delegates' shares MAY overlap on purpose, so that one can pick up what another misses.
- Each delegate MUST trace every claim to its source (e.g., a file path, a URL, a quotation). Where delegates disagree, the combined result MUST say so, rather than pick one.
- A review SHOULD run in a fresh context that has the artefact and its requirements, but not the reasoning that produced it.

## Offloading

_Context offloading_ is keeping information outside the context (e.g., in a file, in an issue tracker), for the agent to read back when it needs it.

- A deliverable that outlives the session, or that someone else needs, MUST be written outside the context (e.g., to a file, as a comment on an issue), and passed on by reference.
- Exact details that later work needs (e.g., paths, identifiers, error messages) MUST be written to a file, rather than left to a summary of the history.
- Where the harness can start a fresh session, long-running work SHOULD be split into sessions bounded by time or tokens, each ending with notes. An agent that stops making progress SHOULD start afresh from its notes and its work, carrying over what failed and why, but not the attempts themselves.

## Pruning

_Context pruning_ is removing from the history what the agent no longer needs.

- Where the harness calls the model itself, and the model allows its history to be edited, old tool output SHOULD be dropped from the history by a fixed rule, and a summary written by a model SHOULD only be added where evals show that it does better.

## Summarisation

_Context summarisation_ is replacing part of the context with a summary of it (aka _compaction_).

- A summary that another agent or a person will act on MUST state the conclusions and the evidence behind them, leaving out how they were reached.
