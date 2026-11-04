# Anthropic Claude

## Opus 5.5

- Opus 5.5 SHOULD run any task that ingests a large corpus, or that divides work between other agents (e.g., research).

## Sonnet 5.5

- A prompt that Sonnet 5.5 will run at low or medium effort (its default in Claude Code) MUST state every step that it must take as an obligation, tied to the task that triggers it, since at those levels it often skips a step that it's only told to take (e.g., loading a skill that it's told to use), and at low effort it often answers without thinking.
