# Harness engineering

## Prompts

- Prompts and prompt templates MUST live in files of their own, so that a person can review each one as the model will read it. Code MAY fill in a template's placeholders with data (e.g., a path, a diff, the task's text), but MUST NOT compose a prompt's instructions.
- Whatever else the model reads as instructions (e.g., a tool's description, a message from a hook) SHOULD live in files beside the prompts too, or else be reviewed and evaluated like them.
- A prompt that a model wrote or optimised (e.g., a skill, an instruction file) MUST be saved to a file and reviewed by a person before it's used, since guidance that models write for themselves has been found not to help.

## Identity and access

- The model MUST act under an identity of its own (e.g., a bot account), never a person's, so that the systems it acts on can tell its actions and approvals from the person's. The identity MUST have no more privileges than the model's tasks need.
- An action that would reach people beyond those who asked for it (e.g., merging into a branch that others install from, publishing a release) MUST require a person's approval, enforced by the system that the action goes through (e.g., a branch ruleset that requires an approving review).
- The harness SHOULD allow whatever is common and can't cause damage without asking (e.g., read-only commands, the project's build and test commands), ask before anything that's irreversible or writes to a shared system (e.g., an arbitrary API call), and refuse writes to files that only a tool may change (e.g., lockfiles). A run that nobody attends MUST refuse any action that would need a person's answer.
- Where the model can run arbitrary commands, access controls SHOULD be enforced by the operating system (e.g., with nono), so that they hold whatever the model runs.
- Within a session, a model MUST NOT have untrusted input (e.g., a web page, an issue filed by a stranger), access to private data, and a way to communicate externally or change state, all at once. Where all three are unavoidable, each consequential action MUST pass a deterministic check or a person's approval.
- Approvals MUST reach the model through the harness (e.g., a permission prompt), and a claim of approval in a brief or in another agent's message MUST NOT count as one, since models have invented a person's approval when briefing another agent.
- Third-party skills, plugins, and instruction files, including any scripts that come with them, MUST be reviewed like any other dependency before they're installed.

## Sandboxes

- A model that runs commands SHOULD do so in an ephemeral sandbox, created for the task and destroyed after it, whether local (e.g., a Docker container, a virtual machine) or remote (e.g., an EC2 instance).
- An agent that acts without approval for each action MUST run in a sandbox that isolates both its filesystem and its network.
- Network access from a sandbox MUST be denied by default, and allowed host by host.
- A sandbox MUST NOT hold any credential or data that the task doesn't need (e.g., production credentials). Credentials SHOULD stay outside it, added to each request by a proxy that checks the request.
- Work SHOULD only leave a sandbox through a channel that a deterministic check controls (e.g., a branch that can't be merged without approval).
- Agents that work in parallel MUST each work on their own copy of whatever they change (e.g., a Git worktree per task), so that none can overwrite another's work.

## Checks

- A check that serves as a guardrail (e.g., a hook that blocks a command) MUST fail closed: if it crashes, times out, or returns something malformed, the action MUST be blocked.
- A check on the commands that a model runs SHOULD parse each command, rather than match it against a pattern, and SHOULD be backed by a check of the result once the run ends, since a model that's blocked may pursue its goal another way (e.g., deleting a file from a script once `rm` is denied).
- Messages that the model reads from checks, hooks, and tools MUST say what's wrong and how to fix it.
- Output that code consumes SHOULD be constrained by a schema that the platform enforces.

## Runs

- Every run MUST be capped in turns, time, and spend (e.g., 30 turns and 20 minutes for Claude Code in CI), by the harness rather than by the model, and MUST be stoppable from outside.
- Every run MUST leave a complete transcript (e.g., its inputs, its tool calls and their results, what was refused, and what it cost).
- The harness MUST be pinned to an exact version, and updated through a change that's reviewed like any other, since a new version can change how it treats a prompt (e.g., how it resolves a skill's name).
- An outer harness MUST pin everything that the harness it runs loads (e.g., instructions, hooks, plugins, tool servers), and SHOULD fail the run where any of them didn't load.
