# Software Development Lifecycle (SDLC) Plugin

This plugin provides the building blocks of AI software factories: agents for the roles needed to deliver a product or a change to it, and skills for the guidelines that those roles follow.

The prompt or harness decides who each escalation goes to, and provides any process or tooling that they rely on. For example, if the human in the loop cares about a product's systems architecture and user experience, but not its code, the harness would send escalations about the code or the software architecture to another programmer agent, and those about the systems architecture or the user experience to the human.

The agents and skills are meant to work well on any model at least as capable as Opus 5.5, so their evals only run on Opus 5.5.

## Agents

An agent is a job description: the priorities it optimises for, and the principles by which it delivers on them. It says what the role must achieve and why, and leaves how to the model's judgement.

```markdown
---
name: (slug)
description: (Role title). Use to (primary deliverables); or to review (artefacts). You SHOULD tell it what you want, but not how to do it.
skills:
  - (Skill relevant to every task this role performs)
  - sdlc:escalation
---
# (Role title)

(Responsibilities.)

(How the role's work shapes the domains that it doesn't own.) However, you don't own any of them, so you MUST NOT (what the role mustn't do in them), even where you're asked to.

Before you review an artefact that you didn't produce (e.g., (examples of what the role reviews)), or process feedback on an artefact that you produced, you MUST load the `artefact-review` skill and follow it.

## Priorities

(Ordered: earlier beats later when they conflict.)

## Principles

(How to deliver on the priorities, in broad terms, in the order of the priorities that they serve.)

## Escalation

(Hazards specific to the role's domain, in the same format as those in the `escalation` skill.)
```

## Skills

Anything prescriptive (conventions, workflows, templates, checklists) belongs in a skill. A skill that an agent preloads MUST make the agent's principles concrete (e.g., how to apply them, what to check), and MUST NOT merely restate them.

## Conventions

- Agents and skills MUST NOT name another agent, a role, or a person, so that they compose with any caller.
- Agents and skills MUST NOT assume any development process or tooling, so that they compose with any harness.
- Skills and agents MUST refer to a skill by its bare name in their instructions (e.g., the `escalation` skill), since the slash and the plugin prefix (e.g., `/sdlc:escalation`) are specific to Claude Code.
- Agents MUST list each skill under `skills:` with its plugin prefix (e.g., `sdlc:escalation`), since Claude Code otherwise loads the skill of that name from whichever plugin it loaded first.
- A skill that extends another MUST only cover what changes in its domain, and the skill it extends MUST NOT cover anything specific to that domain, so that no instruction appears in both. The skills that extend another are:
  - `protocol-design`, which extends `systems-architecture` with what's specific to protocols, including cryptographic ones.
- In skills, only `SKILL.md` MAY link to the skill's other files (e.g., reference files, templates), so that every relative path resolves from the skill's root. Any other file MAY refer to them by name instead (e.g., "the report template").
- In templates, placeholders MUST be written in parentheses, whether they stand for a value or for a passage of text (e.g., `# (System) threat model`, `(What the model covers, and what it leaves out.)`).
- Every instruction MUST come from how I work, rather than from received wisdom.
- A change that bases an instruction on findings from someone else's work (e.g., a paper, a post) MUST credit the work in `CREDITS.md`, unless it's already credited there, or the instruction names it (e.g., a principle, a tool).
- When changing an agent or skill, you MUST consider whether its counterpart (e.g., the `programming` skill for the `programmer` agent) needs a matching change.
- You MUST observe the /ghost-writing:ghost-writing skill.

## Pull requests

CI releases the plugin from the squash commit of each pull request, which takes the pull request's title and description. semantic-release works out the version and the release notes from them.

- Titles MUST follow [Conventional Commits](https://www.conventionalcommits.org), with one of the following types:
  - `feat`: A new agent, skill, or instruction, which releases a minor version.
  - `fix`: Any other change to an agent or a skill (e.g., a corrected or reworded instruction), which releases a patch.
  - `refactor`: A change to code (e.g., the evals' runner) that doesn't change what it does.
  - `docs`: A change to the documentation, such as the README or `CREDITS.md`.
  - `test`: A change to the evals.
  - `ci`: A change to the CI workflows or their scripts.
  - `chore`: A change to the tooling or the dependencies.
  - `revert`: A reverted change, which releases a patch if the description says `This reverts commit (SHA).`
- A change to an agent or a skill MUST have a type that releases a version, since existing users only get it with a new version. The check refuses any other type.
- A title MUST put `!` after the type (e.g., `feat!: Rename the ...`) when the change renames or removes an agent or a skill, since callers refer to them by name. That releases a major version.
- A line in the description MUST NOT start with `BREAKING CHANGE` (in any case, even after `*` or `|`) unless the change is breaking, since that also releases a major version.
- The `version` in `.claude-plugin/plugin.json` MUST NOT be changed by hand, except on a pull request from a fork, whose branch CI can't push to. CI sets it to the version of the release, in a commit of its own on the pull request's branch, and the check says which version that is.
- The squash commit's message MUST NOT be edited when merging. Edit the pull request's title or description instead, so that CI checks the version again.
