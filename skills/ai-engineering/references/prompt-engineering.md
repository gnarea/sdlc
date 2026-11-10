# Prompt engineering

- A prompt SHOULD hold as few instructions as do the job, since an agent follows fewer of them as their number and the length of the session grow.
- Each instruction MUST appear in one place only. Where several prompts need it, it MUST move to a skill or a file that they all load, so that no two copies can contradict each other.
- Instructions MUST NOT pull in opposite directions. Where two goals can conflict, the prompt MUST say which one wins (e.g., by listing priorities in order).
- An instruction that only applies to some tasks MUST say which ones, so that the agent doesn't apply it to the rest.
- Each instruction MUST be concrete enough to tell whether it was followed (e.g., "Use 2-space indentation", rather than "Format the code properly").
- Each instruction MUST be checked for what it invites, as well as for what it says (e.g., asking for a document with enough detail to be "built without guesswork" invites implementation detail, and describing the assumptions in a result's schema as "the choices that you made for the maintainers" invites the agent to make a decision that needs their confirmation, and to record it as an assumption).
- An instruction SHOULD give its reason where the agent needs it to apply the instruction to cases that the prompt doesn't foresee.
- An instruction that compensates for a weakness of a model SHOULD name the model and the weakness (e.g., "since Sonnet 5.5 often skips a skill that it's only told to use"), so that it can be removed once no model that runs the prompt has the weakness.
- A change that fixes a defect or adds a behaviour SHOULD consider simplifying or restructuring the prompt (e.g., rewording, merging, or removing instructions), as well as, or instead of, adding to it.
- Examples SHOULD be several and varied, since a model may copy an example's length, tone, and structure.
- A prompt that asks for a document SHOULD ask for a length that matches what the task needs, with each point made once.
- A concept SHOULD be explained in the prompt, rather than linked. A prompt MUST NOT link to anything that the agent doesn't need to open, since the agent may follow the link.
- A prompt MUST NOT refer to how it came about (e.g., an issue, a pull request, an incident).

## System and user prompts

A _system prompt_ defines a task in general terms, so that it holds for every case that an agent is given (e.g., an agent's definition), whereas a _user prompt_ applies the task to one case, much like a function's declaration and the arguments passed to one call of it.

- Whatever holds for every case (e.g., the agent's role, its rules, the form of its output) SHOULD go in the system prompt, and the user prompt SHOULD only hold what's specific to the case at hand (e.g., what to apply the task to, a decision already made about it, work already done on it).
- A system prompt SHOULD only prescribe how to do the task where the task leaves no room for judgement (e.g., extracting the same fields from every email). Otherwise, it SHOULD give the goal, the priorities, and the constraints, and leave the method to the agent, so that the agent can find what nobody anticipated.
- Where an agent is meant to use its own judgement, its system prompt SHOULD read as a job description: what the role owns, its priorities in order, the principles by which it delivers on them, and the hazards that it must escalate, with anything prescriptive in a skill.
- A system prompt SHOULD be brief, with whatever only some cases need loaded only when they need it (aka _progressive disclosure_), such as from a skill and its reference files.
- Where the task is open-ended (e.g., research), the user prompt SHOULD spell out what to look for, whilst leaving room for findings that nobody anticipated.

## Project instructions

_Project instructions_ are the files that every agent working on a project loads at the start of each session (e.g., `AGENTS.md`, `CLAUDE.md`).

- Project instructions MUST only hold what's relevant to every agent that works on the project, and that agents can't discover for themselves (e.g., a convention that departs from the norm, the commands for common tasks), since every agent loads them, whereas specialised agents each need different things. They SHOULD then be succinct (e.g., under 100 lines), and MUST point to the project's other documents, rather than repeat them.
- What only some agents need SHOULD go in instructions of their own (e.g., an agent's definition, a skill that the agent preloads, a rule scoped to some files).

## Skills

A _skill_ is a set of instructions that an agent loads when a task calls for it, along with any files that come with them (e.g., reference files, templates, scripts).

- `SKILL.md` MUST only hold what applies to every task that the skill covers, and MUST link to a reference file for anything else, saying when each one applies.
- Only `SKILL.md` MAY link to the skill's other files, so that every relative path resolves from the skill's root.
- The description of a skill or an agent MUST say what it covers and when to use it, in the terms that a matching request would use.
- A skill that applies to every task that an agent performs SHOULD be loaded with the agent's system prompt, rather than left for the agent to load when its description matches.
- Where a skill or an agent is chosen by its description, evals MUST check whether it's chosen separately from whether it helps.

## Portability

A prompt is _portable_ where it must work with more than one model or harness (e.g., a plugin that others install in the harness of their choosing).

- Whether a prompt must be portable, and with which models and harnesses, MUST be decided before it's written, as it depends on who will run it.
- A portable prompt MUST NOT depend on anything specific to one model or harness, such as a development process, a tool, or a harness's syntax for invoking a skill (e.g., it refers to the `escalation` skill, rather than to `/sdlc:escalation` as in Claude Code).
- A portable skill MUST conform to the [Agent Skills specification](https://agentskills.io/specification).
- The evals of a portable prompt MUST cover each model and harness that it must work with.
