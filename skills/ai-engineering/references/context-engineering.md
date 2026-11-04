# Context engineering

The _context_ is everything that the model has in front of it when it responds: its prompts, whatever it has read (e.g., files, tool results), and the history of the session.

## Augmentation

_Context augmentation_ is giving the model the information that a task needs (e.g., in the prompt, through a search index, in a skill).

- What every task needs SHOULD be front-loaded (e.g., in the system prompt), and what only some tasks need SHOULD be loaded when they need it (e.g., from a skill, a reference file, or a document that the prompt points to).
- A project's instructions for agents (e.g., `CLAUDE.md`) MUST be succinct (e.g., under 100 lines), and MUST point to the project's other documents, rather than repeat them.

## Quarantine

_Context quarantine_ is giving part of the work to another agent, which starts with an empty history (e.g., a subagent).

- Work SHOULD be delegated where it would fill the context with material that the rest of the work doesn't need (e.g., researching a large corpus).
- Where the input is large, it SHOULD be divided between delegates, each owning one deliverable, and each delegate SHOULD be encouraged to divide its share in turn.
- Where missing something would be costly, the delegates' shares MAY overlap on purpose, so that one can pick up what another misses.
- Each delegate MUST trace every claim to its source (e.g., a file path, a URL, a quotation). Where delegates disagree, the combined result MUST say so, rather than pick one.

## Offloading

_Context offloading_ is keeping information outside the context (e.g., in a file, in an issue tracker), for the model to read back when it needs it.

- A deliverable that outlives the session, or that someone else needs, MUST be written outside the context (e.g., to a file, as a comment on an issue), and passed on by reference.

## Summarisation

_Context summarisation_ is replacing part of the context with a summary of it (aka _compaction_).

- A summary that another agent or a person will act on MUST state the conclusions and the evidence behind them, leaving out how they were reached.
