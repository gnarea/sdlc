# Anthropic Claude

## Choosing a model and its effort

- Opus 5.5 SHOULD be the default, starting at medium effort, and the effort level SHOULD be raised before another model is tried.
- Opus 5.5 SHOULD run any task that ingests a large corpus, or that divides work between other agents (e.g., research).
- Fable 5.1 SHOULD only run a task for which evals show Opus 5.5 falling short at its highest effort levels.
- Haiku 5.5 SHOULD only run narrow tasks whose output is checked (e.g., searching, extracting, classifying).
- A design that mixes models (e.g., a cheaper model for the subagents) SHOULD be compared in evals with the strongest of them alone at a lower effort level before it's adopted.
- Each model MUST be named by its full ID (e.g., `claude-sonnet-5-5`), rather than by an alias (e.g., `sonnet`), since an alias can resolve to an older model (e.g., on some cloud providers).
- How much a model thinks MUST be set through its effort level, for each agent, rather than by telling it to think more or less. Each model MUST get a level of its own, since the same level means a different amount of thinking on each model, and harnesses default to different levels (e.g., Claude Code runs Sonnet 5.5 at medium, whereas the API runs it at high).
- Data that mustn't be retained MUST NOT be sent to Fable 5.1, since it isn't offered with zero data retention.

## Every model

- An instruction that's meant to apply broadly MUST say so (e.g., "before every review"), since Claude doesn't extend an instruction to cases that it doesn't name, least of all at low effort.
- Emphasis other than the keywords that grade an obligation (e.g., "CRITICAL", "IMPORTANT", text in capitals) SHOULD only be added where evals show Claude under-weighting the instruction, since emphasis makes it over-apply the rule.
- Prompts, skills, and tools' parameters MUST NOT ask Fable 5.1, Opus 5.5, or Sonnet 5.5 to write out its reasoning, since they may refuse. They MAY ask for a short explanation, or a summary of what was done.
- Examples SHOULD be several and varied, since Claude copies an example's length, tone, and structure.
- A prompt that asks for a document SHOULD ask for a length that matches what the task needs, with each point made once.
- An agent that runs in a sandbox SHOULD be told what the sandbox allows, since Claude is then far less likely to reach outside it.
- Text that a harness adds to a session (e.g., a hook's message, a notice between steps) SHOULD be written as facts, and SHOULD follow the last tool result as text of its own, since Claude may otherwise take it for a prompt injection.
- Where the harness calls the model itself, the system prompt and the tool list MUST stay identical, byte for byte, throughout a session, and the history MUST only be appended to, since an edit invalidates the cache and the model's earlier thinking, and the API may refuse it. Changes SHOULD go in as messages, and the history SHOULD be compacted by the API, or the session restarted from files.

## Fable 5.1

- A prompt for Fable 5.1 SHOULD describe the outcome, rather than the steps, since prompts and skills written for earlier models are often too prescriptive for it, and lower the quality of its work.
- A prompt for an unattended run SHOULD tell Fable 5.1 that nobody is watching, since it otherwise stops to ask for permission that it already has.
- A harness SHOULD NOT show Fable 5.1 how many tokens it has left.

## Opus 5.5

- Untrusted content SHOULD reach Opus 5.5 through a tool result, rather than in a user message (e.g., pasted into a brief), since it treats whatever is in a user message as coming from the user.

## Sonnet 5.5

- A prompt that Sonnet 5.5 will run at low or medium effort (its default in Claude Code) MUST state every step that it must take as an obligation, tied to the task that triggers it, since at those levels it often skips a step that it's only told to take (e.g., loading a skill that it's told to use), and at low effort it often answers without thinking.
- Where the quality of its work matters, Sonnet 5.5 SHOULD run at high effort, since it does markedly worse at medium.
- A prompt SHOULD NOT discourage Sonnet 5.5 from using tools or skills in general terms (e.g., "minimise tool calls"), since it follows such lines literally. A tool to avoid SHOULD be named, along with when to avoid it.

## Haiku 5.5

- Haiku 5.5 SHOULD run at high effort where it must follow instructions closely, and SHOULD NOT run at low effort with a long system prompt, since it then tends to stop early and hand the task back.
