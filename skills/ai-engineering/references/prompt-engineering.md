# Prompt engineering

A _prompt_ is any text that instructs a model: a system prompt, a user prompt, or a skill.

## Every prompt

- A prompt SHOULD hold as few instructions as do the job, since a model follows fewer of them as their number and the length of the session grow.
- Each instruction MUST appear in one place only. Where several prompts need it, it MUST move to a skill or a file that they all load, so that no two copies can contradict each other.
- Instructions MUST NOT pull in opposite directions. Where two goals can conflict, the prompt MUST say which one wins (e.g., by listing priorities in order).
- An instruction that only applies to some tasks MUST say which ones, so that the model doesn't apply it to the rest.
- Each instruction MUST be concrete enough to tell whether it was followed (e.g., "Use 2-space indentation", rather than "Format the code properly").
- Each instruction MUST be checked for what it invites, as well as for what it says (e.g., asking for a document with enough detail to be "built without guesswork" invites implementation detail).
- An instruction SHOULD give its reason where the model needs it to apply the instruction to cases that the prompt doesn't foresee.
- An instruction that compensates for a weakness of a model SHOULD name the model and the weakness (e.g., "since Sonnet 5.5 often skips a skill that it's only told to use"), so that it can be removed once no model that runs the prompt has the weakness.
- Examples MUST be consistent with the instructions that they illustrate, since a model may follow an example over an instruction that it contradicts.
- A concept SHOULD be explained in the prompt, rather than linked. A prompt MUST NOT link to anything that the model doesn't need to open, since the model may follow the link.
- A prompt MUST NOT refer to how it came about (e.g., an issue, a pull request, an incident).
- A prompt that more than one caller uses (e.g., an agent, a skill) MUST NOT name another agent, a role, or a person, so that it works with any caller.
- In a template that the model fills in, placeholders MUST be written in parentheses, and the model MUST be told to leave out any section that has nothing in it.

## System prompts

A _system prompt_ sets the role that the model plays across every task that it's given (e.g., an agent's definition).

- A system prompt for a role SHOULD read as a job description: what the role owns, its priorities in order, the principles by which it delivers on them, and the hazards it must escalate. Anything prescriptive (e.g., a convention, a workflow, a template, a checklist) MUST go in a skill instead.
- An agent's description SHOULD tell callers to say what they want, but not how to do it.
- Where a harness loads skills for an agent by name (e.g., the `skills` field of a Claude Code agent), each name SHOULD be qualified by its plugin (e.g., `sdlc:escalation`), since an unqualified name may resolve to another plugin's skill.

## User prompts

A _user prompt_ assigns a task.

- A user prompt MUST say what's wanted, why, where the result goes (e.g., a file, a comment on an issue), and how to tell when it's done. It MUST pass on whatever the model can't discover for itself (e.g., a constraint, a decision already made, work already done).
- A user prompt SHOULD NOT say how to do the task, unless a step is fragile (e.g., a command that must be run exactly as given).
- Where the task is open-ended (e.g., research), the prompt SHOULD spell out what to look for, whilst leaving room for findings that nobody anticipated.

## Skills

A _skill_ is a set of instructions that the model loads when a task calls for it, along with any files that come with them (e.g., reference files, templates, scripts).

- `SKILL.md` MUST only hold what applies to every task that the skill covers, and MUST link to a reference file for anything else, saying when each one applies.
- Only `SKILL.md` MAY link to the skill's other files, so that every relative path resolves from the skill's root.
- A prompt that relies on a skill MUST tell the model to load it before the task that it covers (e.g., "Before you review (…), you MUST load the `artefact-review` skill"), since some models (e.g., Sonnet 5.5) often skip a skill that they're only told to use.
