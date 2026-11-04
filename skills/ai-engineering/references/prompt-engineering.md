# Prompt engineering

A _prompt_ is any text that instructs a model: a system prompt, a user prompt, or a skill.

## Every prompt

- Each instruction MUST come from the practice of those the model works for (e.g., their conventions, a failure observed in the model's output), rather than from received wisdom.
- Each instruction MUST appear in one place only. Where several prompts need it, it MUST move to a skill or a file that they all load, so that no two copies can contradict each other.
- Instructions MUST NOT pull in opposite directions. Where two goals can conflict, the prompt MUST say which one wins (e.g., by listing priorities in order).
- An instruction that only applies to some tasks MUST say which ones, so that the model doesn't apply it to the rest.
- Each instruction MUST be checked for what it invites, as well as for what it says (e.g., asking for a document with enough detail to be "built without guesswork" invites implementation detail).
- An instruction SHOULD give its reason where the model needs it to apply the instruction to cases that the prompt doesn't foresee.
- A concept SHOULD be explained in the prompt, rather than linked. A prompt MUST NOT link to anything that the model doesn't need to open, since the model may follow the link.
- A prompt MUST NOT refer to how it came about (e.g., an issue, a pull request, an incident).
- A prompt that's reused by more than one caller or harness (e.g., an agent, a skill) MUST NOT name another agent, a role, or a person, nor assume a development process or tooling, so that it works with any of them.
- In a template that the model fills in, placeholders MUST be written in parentheses, and the model MUST be told to leave out any section that has nothing in it.

## System prompts

A _system prompt_ sets the role that the model plays across every task that it's given (e.g., an agent's definition).

- A system prompt for a role SHOULD read as a job description: what the role owns, its priorities in order, the principles by which it delivers on them, and the hazards it must escalate. Anything prescriptive (e.g., a convention, a workflow, a template, a checklist) MUST go in a skill instead.
- The description that callers see when choosing an agent MUST say what to use it for, and SHOULD tell them to say what they want, but not how to do it.
- Where a harness loads skills for an agent by name (e.g., the `skills` field of a Claude Code agent), each name SHOULD be qualified by its plugin (e.g., `sdlc:escalation`), since an unqualified name may resolve to another plugin's skill.

## User prompts

A _user prompt_ assigns a task.

- A user prompt MUST say what's wanted, why, and where the result goes (e.g., a file, a comment on an issue), and MUST relay any constraint that the model can't infer. It SHOULD NOT say how to do the task.
- Where the task is open-ended (e.g., research), the prompt SHOULD spell out what to look for, whilst leaving room for findings that nobody anticipated.

## Skills

A _skill_ is a set of instructions that the model loads when a task calls for it, along with any files that come with them (e.g., reference files, templates, scripts).

- A skill MUST conform to the [Agent Skills specification](https://agentskills.io/specification), so that any harness that implements it can load the skill.
- `SKILL.md` MUST only hold what applies to every task that the skill covers, and MUST link to a reference file for anything else, saying when each one applies.
- Only `SKILL.md` MAY link to the skill's other files, so that every relative path resolves from the skill's root.
- Where a step in a skill can be deterministic, the skill SHOULD come with a script that performs it.
- Instructions MUST refer to a skill by its bare name (e.g., the `escalation` skill), since each harness has its own syntax for invoking one (e.g., `/sdlc:escalation` in Claude Code, `/skill:escalation` in Pi).
- A prompt that relies on a skill MUST tell the model to load it before the task that it covers (e.g., "Before you review (…), you MUST load the `artefact-review` skill"), since a model may skip a skill that it's only told to use.
