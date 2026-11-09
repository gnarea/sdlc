# Anthropic Claude

- Each model SHOULD be named by its full ID (e.g., `claude-sonnet-5-5`), rather than by an alias (e.g., `sonnet`), since an alias can resolve to an older model (e.g., on some cloud providers).
- A design that mixes models (e.g., a cheaper model for the agents that another delegates to) SHOULD be compared in evals with the strongest of them alone at a lower effort level before it's adopted.
- How much a model thinks MUST be set through its effort level, for each agent, rather than by telling it to think more or less. The level SHOULD be chosen in evals for each model, rather than carried over from another, since the same level means a different amount of thinking on each model.
- An instruction that's meant to apply broadly MUST say so (e.g., "before every review"), since Claude doesn't extend an instruction to cases that it doesn't name, least of all at `low` effort.
- Emphasis other than the keywords that grade an obligation (e.g., "CRITICAL", "IMPORTANT", text in capitals) SHOULD only be added where evals show Claude under-weighting the instruction, since emphasis makes it over-apply the rule.
- Prompts, skills, and tools' parameters MUST NOT ask the model to write out its reasoning, since it may refuse. They MAY ask for a short explanation, or a summary of what was done.
- A prompt that embeds material alongside its instructions (e.g., a template that code fills in with inputs, a brief that includes documents or examples) SHOULD mark off each kind of material with an XML tag of its own (e.g., `<input>`, `<example>`), with the same descriptive names across prompts, nested where the material nests (e.g., each `<document>` inside `<documents>`). The instructions themselves MAY stay in Markdown (e.g., in a skill, an agent's definition, or project instructions).
- Where the embedded material is long (e.g., documents of over 20,000 tokens), it SHOULD come first in the prompt, before the instructions and the question, and each document SHOULD carry its source in a tag of its own (e.g., `<source>`).
- Text that a harness adds to a session (e.g., a message from code that runs after a tool call, a notice between steps) SHOULD be written as facts, and SHOULD follow the last tool result as text of its own, since Claude may otherwise take it for a prompt injection.
- Where the harness calls the model itself, the system prompt and the tool list MUST stay identical, byte for byte, throughout a session, and the history MUST only be appended to, since an edit invalidates the cache and the model's earlier thinking, and the API may refuse it. Changes SHOULD go in as messages, and the history SHOULD be compacted by the API, or the session restarted from what's been written down.

## Fable 5.2

Fable 5.2 SHOULD only run exceptional work that justifies the greatest capability available (e.g., research across many sources that ends in a finished document), and only where evals show Opus 5.5 falling short at its highest effort levels, or Fable 5.2 doing as well for less at a lower level.

Its effort SHOULD start at `high`, its default on the API, rising to `xhigh` for the hardest long-running work where evals show a gain, and falling to `medium` or `low` where evals show that quality holds. It SHOULD only run at `max` to measure its ceiling, or for the rare task where time and tokens don't matter.

- Data that mustn't be retained MUST NOT be sent to Fable 5.2, unless Anthropic has expressly authorised zero data retention for the account, since Fable 5.2 otherwise requires data to be retained for 30 days.
- Where Fable 5.2 ends a turn before the work is done, as it's more likely to do at `low` and `medium` effort, its prompt SHOULD tell it to carry on with any work that doesn't depend on someone's answer, working through ordinary obstacles (e.g., an error, a timeout), and leaving deliberate ones alone (e.g., access that was withheld).
- An approval rule in a prompt for Fable 5.2 SHOULD name the exact actions that it covers, with any exception written into the rule itself, and the prompt SHOULD name the routine steps that need no approval (e.g., retrying a call that's safe to repeat), since Fable 5.2 applies such rules as written, and holds back routine work otherwise.
- A harness SHOULD NOT tell Fable 5.2 in its prompt how many tokens it may use or has left, since how much it spends depends on the budget's size, and it does as well without a large one.
- Rules on Fable 5.2's writing style SHOULD NOT set hard limits (e.g., "one instruction per sentence, in 20 words or fewer"), since it follows them closely enough to make its prose choppy.

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
