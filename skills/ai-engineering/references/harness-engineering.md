# Harness engineering

## Prompts

- Prompts and prompt templates MUST live in files of their own, so that a person can review each one as the model will read it. Code MAY fill in a template's placeholders, but MUST NOT compose a prompt's instructions.

## Identity and access

- The model MUST act under an identity of its own (e.g., a bot account), never a person's, so that the systems it acts on can tell its actions and approvals from the person's. The identity MUST have no more privileges than the model's tasks need.
- An action that would reach people beyond those who asked for it (e.g., merging into a branch that others install from, publishing a release) MUST require a person's approval, enforced by the system that the action goes through (e.g., a ruleset that requires a code owner's review).
- The harness SHOULD allow whatever is common and can't cause damage without asking (e.g., read-only commands, the project's build and test commands), ask before anything that writes to a shared system (e.g., an arbitrary API call), and refuse writes to files that only a tool may change (e.g., lockfiles).
- Where the model can run arbitrary commands, access controls SHOULD be enforced by the operating system (e.g., with nono), so that they hold whatever the model runs.

## Sandboxes

- A model that runs commands SHOULD do so in an ephemeral sandbox, created for the task and destroyed after it, whether local (e.g., a Docker container, a virtual machine) or remote (e.g., an EC2 instance).
- A sandbox MUST NOT hold any credential or data that the task doesn't need (e.g., production credentials).
- Agents that work in parallel MUST each work on their own copy of whatever they change (e.g., a Git worktree per task), so that none can overwrite another's work.

## Runs

- Every run MUST be capped in turns and in time (e.g., 30 turns and 20 minutes for Claude Code in CI).
- The harness MUST be pinned to an exact version, and updated through a change that's reviewed like any other, since a new version can change how it treats a prompt (e.g., how it resolves a skill's name).
