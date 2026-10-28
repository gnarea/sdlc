# Software Development Lifecycle (SDLC) Plugin

This plugin provides the building blocks of AI software factories: agents for the roles needed to deliver a product or a change to it, and skills for the guidelines that those roles follow.

The prompt or harness decides who each escalation goes to, and provides any process or tooling that they rely on. For example, if the human in the loop cares about a product's systems architecture and user experience, but not its code, the harness would send escalations about the code or the software architecture to another programmer agent, and those about the systems architecture or the user experience to the human.

## Agents

An agent is a job description: the priorities it optimises for, and the principles by which it delivers on them.

```markdown
---
name: (slug)
description: (Role title). Use to (primary deliverables); or to review (artefacts).
skills:
  - (Skill relevant to every task this role performs)
  - sdlc:escalation
---
# (Role title)

(Responsibilities.)

Before you review an artefact that you didn't produce (e.g., (examples of what the role reviews)), or process feedback on an artefact that you produced, you MUST load the `artefact-review` skill and follow it.

## Priorities

(Ordered: earlier beats later when they conflict.)

## Principles

(How to deliver on the priorities, in broad terms.)

## Escalation

(Hazards specific to the role's domain, in the same format as those in the `escalation` skill.)
```

## Skills

Anything prescriptive (conventions, workflows, templates, checklists) belongs in a skill.

## Conventions

- Agents and skills MUST NOT name another agent, a role, or a person, so that they compose with any caller.
- Agents and skills MUST NOT assume any development process or tooling, so that they compose with any harness.
- Agents MUST list each skill under `skills:` with its plugin prefix (e.g., `sdlc:escalation`), since Claude Code otherwise loads the skill of that name from whichever plugin it loaded first.
- Agents MUST tell the model to load any other skill before the task that it covers (e.g., "Before you review (…), you MUST load the `artefact-review` skill"), since Sonnet 5.5 often skips a skill that it's only told to use.
- Every instruction MUST come from how I work, rather than from received wisdom.
- When changing an agent or skill, you MUST consider whether its counterpart (e.g., the `programming` skill for the `programmer` agent) needs a matching change.
- You MUST observe the /ghost-writing:ghost-writing skill.
