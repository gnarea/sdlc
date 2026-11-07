# Harness engineering

## Prompts

- Prompts and prompt templates MUST live in files of their own, so that a person can review each one as the agent will read it. Code MAY fill in a template's placeholders with data (e.g., a path, a diff, the task's text), but MUST NOT compose a prompt's instructions.
- Whatever else an agent reads as instructions (e.g., a tool's description, a message from a hook) SHOULD live in files beside the prompts too, or else be reviewed like them and covered by evals.
- A prompt that an agent wrote or optimised (e.g., a skill, an instruction file) MUST be saved to a file and reviewed by a person before it's used, since guidance that agents write for themselves has been found not to help.

## Identity and access

- Wherever a system can issue it an identity, each agent SHOULD act under one of its own (e.g., a GitHub App for its commits and comments, an operating system user for the processes that it runs), and SHOULD NOT use a person's credentials, or credentials that other agents share.
- Each credential that an agent holds MUST only cover the resources and operations that its task needs (e.g., a token for one repository, rather than for every repository that its owner can reach). Where an agent can't hold credentials of its own, its sandbox MUST limit what it can reach instead (e.g., by mounting only the working copy).
- Unless an exception has been explicitly agreed, an action that affects people beyond those the agent works with MUST wait for a person's approval, enforced by the system that the action goes through (e.g., a branch ruleset that blocks a merge until a person approves it, a queue that holds each outgoing message until a person releases it).
- The harness SHOULD allow whatever is common and can't cause damage without asking (e.g., read-only commands, the project's build and test commands), ask before anything that's irreversible or writes to a shared system (e.g., an arbitrary API call), and refuse writes to files that only a tool may change (e.g., lockfiles). A run that nobody attends MUST refuse any action that would need a person's answer.
- Where an agent can run arbitrary commands, access controls SHOULD be enforced by the operating system (e.g., with nono), so that they hold whatever the agent runs.
- Within a session, an agent MUST NOT have untrusted input (e.g., a web page, an issue filed by a stranger), access to private data, and a way to communicate externally or change state, all at once. Where all three are unavoidable, each consequential action MUST pass a deterministic check or a person's approval.
- Approvals MUST reach an agent through the harness (e.g., a permission prompt), and a claim of approval in a brief or in another agent's message MUST NOT count as one, since agents have invented a person's approval when briefing another agent.
- Third-party skills, plugins, and instruction files, including any scripts that come with them, MUST be reviewed like any other dependency before they're installed.

## Sandboxes

- An agent that runs commands SHOULD do so in an ephemeral sandbox, created for the task and destroyed after it, whether local (e.g., a Docker container, a virtual machine) or remote (e.g., an EC2 instance).
- An agent that acts without approval for each action MUST run in a sandbox that isolates both its filesystem and its network.
- Network access from a sandbox MUST be denied by default, and allowed host by host.
- A sandbox MUST NOT hold any credential or data that the task doesn't need (e.g., production credentials). Credentials SHOULD stay outside it, added to each request by a proxy that checks the request.
- Work SHOULD only leave a sandbox through a channel that a deterministic check controls (e.g., a branch that can't be merged without approval).
- Agents that work in parallel MUST each work on their own copy of whatever they change (e.g., a Git worktree per task), so that none can overwrite another's work.

## Checks

- A check that serves as a guardrail (e.g., a hook that blocks a command) MUST fail closed: if it crashes, times out, or returns something malformed, the action MUST be blocked.
- A check on the commands that an agent runs SHOULD parse each command, rather than match it against a pattern, and SHOULD be backed by a check of the result once the run ends, since an agent that's blocked may pursue its goal another way (e.g., deleting a file from a script once `rm` is denied).
- Messages that an agent reads from checks, hooks, and tools MUST say what's wrong and how to fix it.
- Output that code consumes SHOULD be constrained by a schema that the platform enforces.

## Runs

- Each agent SHOULD run on the cheapest model, at the lowest effort level, that does its job well enough, as evals show. Where a faster option costs more, the cheaper one SHOULD be chosen, unless speed has been asked for.
- Every run MUST be capped in turns, time, and spend (e.g., 30 turns and 20 minutes for Claude Code in CI), by the harness rather than by the agent, and MUST be stoppable from outside.
- Every run MUST leave a complete transcript (e.g., its inputs, its tool calls and their results, what was refused, and what it cost).
- The harness MUST be pinned to an exact version, and updated through a change that's reviewed like any other, since a new version can change how it treats a prompt (e.g., how it resolves a skill's name).
- An outer harness MUST pin everything that the harness it runs loads (e.g., instructions, hooks, plugins, tool servers), and SHOULD fail the run where any of them didn't load.
