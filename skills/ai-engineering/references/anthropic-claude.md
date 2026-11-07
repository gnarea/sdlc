# Anthropic Claude

- Each model SHOULD be named by its full ID (e.g., `claude-sonnet-5-5`), rather than by an alias (e.g., `sonnet`), since an alias can resolve to an older model (e.g., on some cloud providers).
- A design that mixes models (e.g., a cheaper model for the agents that another delegates to) SHOULD be compared in evals with the strongest of them alone at a lower effort level before it's adopted.
- How much a model thinks MUST be set through its effort level, for each agent, rather than by telling it to think more or less. The level SHOULD be chosen in evals for each model, rather than carried over from another, since the same level means a different amount of thinking on each model.
- An instruction that's meant to apply broadly MUST say so (e.g., "before every review"), since Claude doesn't extend an instruction to cases that it doesn't name, least of all at `low` effort.
- Emphasis other than the keywords that grade an obligation (e.g., "CRITICAL", "IMPORTANT", text in capitals) SHOULD only be added where evals show Claude under-weighting the instruction, since emphasis makes it over-apply the rule.
- Prompts, skills, and tools' parameters MUST NOT ask the model to write out its reasoning, since it may refuse. They MAY ask for a short explanation, or a summary of what was done.
- A prompt that mixes kinds of content (e.g., instructions, context, examples, inputs) SHOULD wrap each kind in an XML tag of its own (e.g., `<instructions>`, `<input>`), with the same descriptive names across prompts, nested where the content nests (e.g., each `<document>` inside `<documents>`).
- Long inputs (e.g., documents of over 20,000 tokens) SHOULD come first in a prompt, before the instructions and the question, and each document SHOULD carry its source in a tag of its own (e.g., `<source>`).
- Text that a harness adds to a session (e.g., a message from code that runs after a tool call, a notice between steps) SHOULD be written as facts, and SHOULD follow the last tool result as text of its own, since Claude may otherwise take it for a prompt injection.
- Where the harness calls the model itself, the system prompt and the tool list MUST stay identical, byte for byte, throughout a session, and the history MUST only be appended to, since an edit invalidates the cache and the model's earlier thinking, and the API may refuse it. Changes SHOULD go in as messages, and the history SHOULD be compacted by the API, or the session restarted from what's been written down.

## Fable 5.1

Fable 5.1 SHOULD only run exceptional work that justifies the greatest capability available (e.g., research across many sources that ends in a finished document), and only where evals show Opus 5.5 falling short at its highest effort levels.

Its effort SHOULD start at `high`, its default, rising to `xhigh` or `max` for the most demanding work, and falling to `medium` or `low` for routine work where evals show that quality holds.

- Data that mustn't be retained MUST NOT be sent to Fable 5.1, since it isn't offered with zero data retention.
- A prompt for Fable 5.1 SHOULD describe the outcome, rather than the steps, since prompts and skills written for earlier models are often too prescriptive for it, and lower the quality of its work.
- A prompt for an unattended run SHOULD tell Fable 5.1 that nobody is watching, since it otherwise stops to ask for permission that it already has.
- A harness SHOULD NOT show Fable 5.1 how many tokens it has left.
- Instructions on Fable 5.1's writing style SHOULD go in a user message, rather than in the system prompt, and a nudge that it must act on in every turn SHOULD go at the end of each request, since it gives more weight to both there.

## Opus 5.5

Opus 5.5 SHOULD run complex work that calls for autonomy and judgement (e.g., long-running agentic coding, designing a system, reviewing a change, drawing up a plan), where what's wanted is clearer than how to get there, including any work that ingests a large corpus, or that divides work between other agents (e.g., research).

Its effort SHOULD start at `medium`, its default, rising to `high` or above for harder or longer work, and falling to `low` for routine work where evals show that quality holds.

Untrusted content SHOULD reach Opus 5.5 through a tool result, rather than in a user message (e.g., pasted into a brief), since it treats whatever is in a user message as coming from the user.

## Sonnet 5.5

Sonnet 5.5 SHOULD run well-defined work (e.g., implementing a plan that Opus 5.5 drew up, generating code to a specification).

For agentic work, its effort SHOULD start at `medium` where the task is well specified, and at `high` where it's harder or longer, and it SHOULD only go to `xhigh` or `max` where evals show a gain.

- A prompt that Sonnet 5.5 will run at `low` or `medium` effort MUST state every step that it must take as an obligation, tied to the task that triggers it, since at those levels it often skips a step that it's only told to take (e.g., loading a skill that it's told to use), and at `low` effort it often answers without thinking.
- A prompt SHOULD NOT discourage Sonnet 5.5 from using tools or skills in general terms (e.g., "minimise tool calls"), since it follows such lines literally. A tool to avoid SHOULD be named, along with when to avoid it.

## Haiku 5.5

Haiku 5.5 SHOULD only run narrow, well-defined work (e.g., searching, summarising, extracting, classifying, routing) that doesn't need it to gather much context, or to gather it in complicated ways.

Its effort SHOULD start at `medium`, its default, falling to `low` for short, simple, high-volume requests, and rising to `high` for longer work or strict instruction following. It SHOULD NOT run at `low` effort with a long system prompt, since it then tends to stop early and hand the task back, and it SHOULD only go to `xhigh` or `max` where evals show a gain over Sonnet 5.5.

## Claude Code

Each skill in an agent's `skills` field SHOULD be qualified by its plugin (e.g., `sdlc:escalation`), since an unqualified name may resolve to another plugin's skill.
