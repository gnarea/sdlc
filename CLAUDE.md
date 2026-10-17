# Software Development Lifecycle (SDLC) Plugin

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

You MUST use the /sdlc:artefact-review skill when reviewing an artefact that you didn't produce (e.g., (examples of what the role reviews)).

## Priorities

(Ordered: earlier beats later when they conflict.)

## Principles

(How to deliver on the priorities, in broad terms.)

## Escalation

(Hazards specific to the role's domain, in the same format as those in the escalation skill.)
```

## Skills

Anything prescriptive (conventions, workflows, templates, checklists) belongs in a skill.

## Conventions

- Agents and skills MUST NOT name another agent, a role, or a person, so that they compose with any caller.
- Every instruction MUST come from how I work, rather than from received wisdom.
- When changing an agent or skill, you MUST consider whether its counterpart (e.g., the `programming` skill for the `programmer` agent) needs a matching change.
- You MUST observe the /ghost-writing:ghost-writing skill.
