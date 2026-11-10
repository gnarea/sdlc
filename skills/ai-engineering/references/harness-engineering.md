# Harness engineering

## Prompts

- Prompts and prompt templates MUST live in files of their own, so that a person can review each one as the agent will read it. Every instruction MUST be written in those files, rather than in code, though code MAY render them (e.g., with a templating engine such as Jinja2) and fill them in with data (e.g., a path, a diff, the task's text).
- A prompt that an agent wrote or optimised (e.g., a skill, an instruction file) SHOULD be saved to a file and reviewed independently.

## Untrusted input and output

- An agent's inputs (e.g., a web page, an issue filed by a stranger, a dependency's documentation) MUST be treated as untrusted, since any of them may carry a prompt injection.
- Whatever an agent can change (e.g., source code, its tests, a build's configuration) MUST be treated as untrusted wherever it runs afterwards, since it may do whatever the agent chose (e.g., a test that uploads a credential). It MUST only run where the agent's own commands could.
- Within a session, an agent SHOULD NOT have untrusted input, access to private data, and a way to communicate externally or change state, all at once. Where all three are unavoidable, each consequential action MUST pass a deterministic check, or be approved by whoever the harness authorises to approve it.
- Output that code consumes SHOULD be constrained by a schema that the platform enforces.

## Identity and access

- Wherever a system can issue it an identity, each agent SHOULD act under one of its own (e.g., a GitHub App for its commits and comments, an operating system user for the processes that it runs), and SHOULD NOT use a person's credentials, or credentials that other agents share.
- Each credential that an agent holds SHOULD only cover the resources and operations that its task needs (e.g., a token for one repository, rather than for every repository that its owner can reach).
- Unless an exception has been explicitly agreed, an action that affects people beyond those the agent works with MUST wait for approval from whoever the harness authorises to give it (e.g., a person, another agent), enforced by the system that the action goes through (e.g., a branch ruleset that blocks a merge until an authorised reviewer approves it, a queue that holds each outgoing message until it's released).
- The harness SHOULD allow whatever is common and can't cause damage without asking (e.g., read-only commands that don't expose sensitive data), escalate anything that's irreversible or writes to a shared system (e.g., an arbitrary API call) unless it's been acknowledged up front, and refuse writes to files that only a tool may change (e.g., lockfiles). A run with nobody to escalate to MUST refuse any action that it would otherwise escalate.
- Where nobody can answer an agent before its run ends, whoever runs it (e.g., the harness, the agent that delegated the task) SHOULD give it a place in its result to ask for decisions, so that it can ask without stopping its work. That place SHOULD be apart from the agent's assumptions and the work's open items, since agents seldom ask when stopping is their only way to, and a question amongst assumptions or open items is easily missed. For example, the result's schema could have a field for each decision and the answer that the agent assumed in the meantime, or a delegator could ask for a section of the report on the decisions that the work needs.
- An agent SHOULD only act on an approval that reaches it through the channel that the harness designates for escalations (e.g., from the agent that delegated the task, through a permission prompt), and SHOULD NOT act on one that's claimed anywhere else (e.g., in a file, in a tool's output), since untrusted content may claim an approval that nobody gave.
- Third-party skills, plugins, and instruction files, including any scripts that come with them, MUST be reviewed like any other dependency before they're installed.

## Confinement and isolation

The word _sandbox_ covers two different things, which this reference tells apart: _confinement_ restricts what an agent's processes can do on the machine that they run on (e.g., with nono, which relies on Landlock or Seatbelt), whereas an _isolated environment_ is a machine or container of the agent's own, which holds nothing that would matter if the agent leaked or destroyed it (e.g., a Docker container, a virtual machine, a VPS).

- Every agent SHOULD be confined to the files and hosts that its task needs, whether or not it has an identity of its own (e.g., an agent with its own GitHub App can only connect to GitHub), and one that acts without approval for each action MUST be.
- Confinement SHOULD be enforced by the operating system, so that it holds whatever the agent runs.
- Network access SHOULD be denied by default, and allowed host by host.
- An agent SHOULD be told what its confinement or isolated environment allows, since it's then far less likely to try to reach beyond it.
- An agent that runs commands that could do damage (e.g., the build or the tests of code that it changed) SHOULD do so in an ephemeral isolated environment, created for the task and destroyed after it, whether local (e.g., a Docker container, a virtual machine) or remote (e.g., a VPS).
- An isolated environment MUST NOT hold any credential or data that the task doesn't need (e.g., production credentials). Credentials SHOULD stay outside it, added to each request by a proxy that checks the request.
- Work SHOULD only leave an isolated environment through a channel that a deterministic check controls (e.g., a branch that can't be merged without approval).

## Code around tool calls

Consider having the harness run code before or after an agent's tool calls, or in the background whilst it works:

- Code that runs before a tool call to block it MUST fail closed: if it crashes, times out, or returns something malformed, the call MUST be blocked.
- Where a problem doesn't need blocking (e.g., too many comments in a file that the agent edited), code that runs after the tool call SHOULD point it out to the agent instead, so that the agent can fix it when convenient.
- Code MAY also give the agent context as soon as it's relevant (e.g., pointing it to a file that usually changes along with the one that it just edited), including when work in the background finishes (e.g., a build that the agent started).
- Where code or a tool tells an agent that something's wrong, it SHOULD also say how to fix it.

## Runs

- Each agent SHOULD run on the cheapest model, at the lowest effort level, that does its job well enough, as evals show. Where a faster option costs more, the cheaper one SHOULD be chosen, unless speed has been asked for.
- Every run SHOULD be capped in turns, time, and spend (e.g., 30 turns and 20 minutes for Claude Code in CI), by the harness rather than by the agent, and MUST be stoppable from outside.
- Every run SHOULD leave a complete transcript (e.g., its inputs, its tool calls and their results, what was refused, and what it cost).
- The harness SHOULD be pinned to an exact version, and updated through a change that's reviewed like any other, since a new version can change how it treats a prompt (e.g., how it resolves a skill's name).
