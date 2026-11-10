# Agent eval suite threat model

<!-- cspell:words cspell lockfile worktrees -->

This model covers the agent eval suite described in [the architecture document](architecture.md): the wrapper, the egress proxy, the plugin snapshot, the confined harness and its runs, the case suite, the operator state store, and the invocation temp dir, on the operator's Linux machine.

It leaves out four things:

- The security of the `sdlc` plugin for the people who install it, which concerns the plugin rather than the suite.
- Anthropic's own infrastructure.
- A compromise of the operator's account by means other than the suite.
- Running Claude Code's harness directly, without the suite, which bypasses every mitigation here by design.

## Adversaries

### Authors of an untrusted change

People or agents who change the plugin, its skills, the cases, or the fixtures on a branch that the operator then runs the suite on. These include a coding agent following an injected prompt, and a careless contributor.

- **Goals**: To run code as the operator, to take the credential off the machine, or to make a regression pass or a good agent fail.
- **Capabilities**:
  - Writing any file in the branch, including plugin components, case definitions, fixtures, and changes to the wrapper itself.
  - An agent with a shell in any worktree of the repository can also change the repository's configuration, which every worktree shares and no diff shows.
- **Resources**: Unlimited attempts, since branches are cheap. They are limited by what the operator confirms trust in, and by what a reviewer reads.

### The agent under test

The model, following an agent definition and a case's fixture, which may contain text that steers it.

- **Goals**: None hostile, but it may act on whatever the fixture asks, take actions with effects beyond its workspace, or write output that sways the judge.
- **Capabilities**: The tools that a run is offered, within the confinement, including delegating to other agents, whose tool calls the trace leaves out.
- **Resources**: Up to 4 minutes and its case's turn limit, for each run.

### The operator, or an agent acting for the owner

- **Goals**: None hostile, but they may run the suite more often or more widely than the budget allows, or weaken a protection to get a run through.
- **Capabilities**: Starting the suite, choosing the credential and the cap, confirming trust, and editing the wrapper or the state store.
- **Resources**: The owner's machine and account.

### Other processes under the operator's account

The owner's other sessions and agents on the same machine.

- **Goals**: None hostile, but they can be compromised, or act on injected prompts.
- **Capabilities**: Reading and writing anything the operator's account can, including the state store, the temp dir, and every repository's configuration.
- **Resources**: Running whilst the suite runs.

### A compromised dependency

A malicious release of Claude Code, nono, or an npm package that a merged bump brings in.

- **Goals**: To run code as the operator, or to take credentials off the machine.
- **Capabilities**: Whatever the dependency does: inside the confinement for Claude Code, and outside it for nono and the install-time tooling.
- **Resources**: Those of a supply-chain attacker.

## Attack vectors

### A change brings code that runs during an invocation

The code could arrive as a hook, an MCP or LSP server, a shell command embedded in a skill, a case-level plugin, a case's setup step, or Claude Code configuration or git metadata in a fixture. It could also be a command, such as a git filter, that the repository's configuration names, and that a change's attributes trigger when the wrapper runs git. Or it could be a build backend that the branch's `pyproject.toml` and `uv.lock` make uv run before the wrapper even starts.

- **STRIDE threat type**: Elevation of privilege.
- **Component**: Wrapper, confined harness, and runs.
- **Stakeholders affected**: Operator, owner.
- **Impact**: Code that runs as the operator. Inside the confinement, it can read the credential and send it to any host on the proxy's port. Outside the confinement (for example, through the wrapper's own use of git, a change to the wrapper, or a build that uv runs), it can do anything the operator can.
- **Attempt likelihood**: The highest. Agents write most of the changes, and a case author adding a setup step or a plugin component is an ordinary edit, which needs no malice.
- **Method**: Add the component, key, file, or configuration on a branch or in the repository, and wait for the operator to run the suite on it.
- **Mitigations**:
  - The wrapper takes a snapshot of the plugin and its cases, checks that snapshot, and runs it, so what is checked is what runs.
  - Before starting, it refuses any case key, plugin root entry, manifest component, agent or skill metadata key, fixture content, or setup step that its allowlists do not name.
  - It records the code without running anything that the working tree or the repository's configuration names, using only git commands that run no filters.
  - The operator confirms trust in each worktree before its first invocation. The answer is tied to the worktree's identity on the file system, so a new worktree at an old one's path is asked about afresh.
  - The confinement limits what any code that does run can reach.
- **Residual risks**: The mitigations fall short in four cases:
  - a Claude Code feature that runs code through a key or component the allowlists already permit;
  - a change that a reviewer misses to the wrapper, its allowlists, or the `pyproject.toml` and `uv.lock` that uv reads before the wrapper starts, which costs the attacker only a convincing diff;
  - a way for git, or another tool the wrapper runs, to run a command that the repository's configuration names, which the wrapper does not prevent;
  - an operator who confirms trust without reading the change.

  The operator and the owner bear these risks. They can accept them as long as every change to the wrapper, its allowlists, `pyproject.toml`, `uv.lock`, the setup step, and the pinned harness gets a careful review.

### Spend beyond the approved budget

- **STRIDE threat type**: Denial of service, against the owner's allowance or money.
- **Component**: Wrapper and confined harness.
- **Stakeholders affected**: Owner, and the other sessions and agents on the owner's account.
- **Impact**: The owner loses allowance or money, and their other work loses its share of the allowance and of the rate limit.
- **Attempt likelihood**: High. Invocations are cheap to start, and agents acting for the owner may start them repeatedly or from several worktrees at once. The subscription's utilisation is only reported in whole points, only the provider's responses carry it, and the owner's other sessions move it too.
- **Method**: Repeated or overlapping invocations; a cap set too high; a ledger that is lost or edited, such as a provisional charge removed to get unblocked; a wrapper that dies during a harness call, or a reading that fails; spend that no reading covers.
- **Mitigations**:
  - One invocation at a time under the operator's account, enforced by a lock that the operating system releases when the wrapper exits. A second invocation is refused, rather than left to spend the same remaining budget. The lock and the ledger sit at a fixed place under the account, so a caller's environment cannot give an invocation its own.
  - On the subscription, a usage reading before every harness call, which the wrapper takes itself rather than from the traces, and a stop once the week's charges reach 10 points.
  - A dollar cap on every harness call, which the harness checks before each run: a fixed backstop on the subscription, and what remains of the operator's cap with an API key.
  - A ledger across invocations, keyed by the week's reset time.
  - For each week that its readings touch, each invocation is charged the change in utilisation, all of it attributed to the evals, plus a point for rounding.
  - No harness call on the subscription without a first reading, and no further call once a reading fails.
  - A provisional charge for the rest of the week's budget, written before each harness call and replaced only once the next reading is in. It does not expire with its week, so a wrapper that dies or a reading that fails blocks the subscription until the owner clears it in person, at the controlling terminal.
  - With an API key, a harness call that is interrupted or times out, or whose result cannot be read, is charged its full cap.
  - The wrapper stops every process that a harness call started when the call ends, times out, or is interrupted, so no run outlives its call.
  - A required dollar cap, with no default, for an API key.
  - One run at a time.
- **Residual risks**: The mitigations fall short in five cases:
  - Invocations from another machine, or another user account, on the same subscription are missing from the ledger, so together they can exceed the budget. The owner bears this, and avoids it by running the suite from one machine and account only.
  - A lost or edited ledger forgets this week's spend, which the owner bears until the week resets. That includes a provisional charge that an agent acting for the owner removes by editing the ledger, which the prompt at the controlling terminal does not prevent. Even when the owner clears one in person, what the running call spent after the last reading is forgotten, up to its dollar cap.
  - The harness call that crosses 10 points runs to its end, so the week can exceed 10 points by what that call spends: up to its dollar cap, plus one run. The next reading records it, so no further invocation runs that week.
  - If the provider updates the utilisation some time after a response, the last reading can miss the last call's final requests (most likely the judge's), which then fall between invocations and are never charged. The point added for rounding probably covers them.
  - The readings only carry the seven-day window, so a full run can use much of its 10 points in one sitting, leaving less of any shorter window to the owner's other sessions.

  The owner can accept all five at a 10% budget.

### Results that misattribute an agent's behaviour

- **STRIDE threat type**: Tampering, with the integrity of the results.
- **Component**: Runs, graders, judge, and wrapper.
- **Stakeholders affected**: Owner, and agent and case authors.
- **Impact**: A regression ships, or a good change is rejected.
- **Attempt likelihood**: High, mostly by accident: harness changes, effort downgrades, infrastructure failures, the spend cap, and output that sways the judge all happen without malice.
- **Method**:
  - A harness change alters the runs.
  - The effort is lowered without notice.
  - The confinement refuses an operation that a tool needs.
  - The delegating session fails to delegate.
  - The spend cap stops the judge partway through a harness call.
  - A run is cut short before it does what its case requires.
  - An agent that the agent under test delegates to does work that the agent is credited or blamed for.
  - The agent's output steers the judge, or a case author weakens a grader.
- **Mitigations**:
  - The three outcomes, which treat every cause outside the agent as inconclusive.
  - A run cut short counts as failed only on a prohibition of the trace, which no later step can undo, and only where no other cause makes it inconclusive. No other grader counts on it.
  - A grader of the trace can match only the agent's own calls, which carry a `parent_tool_use_id`, so that work the agent hands to another agent isn't held against it.
  - Each run confirms its effort, using whichever method the pilot settles.
  - The pinned harness, and the tool check after each harness call.
  - The snapshot, so that every harness call runs the same code.
  - The manifest, which ties every result to its code, harness, models, effort, and credential source.
  - Rules grade whatever they can, and the judge only what rules cannot.
- **Residual risks**: The mitigations fall short in eight cases:
  - Runs use the pinned version's default feature flags, so behaviour that a remote flag changes in the owner's own sessions goes untested.
  - Routine runs only test `low`, so a regression that only shows at a higher level ships unless someone runs that level.
  - The agent's output can still steer the judge on criteria that only the judge grades. That includes saying that another agent did the work, in the three domain cases where only the judge decides it.
  - A weakened grader passes a review.
  - A prohibition of the trace whose pattern depends on what follows its match (e.g., through a lookahead) can fail when the run is cut short, and pass at its end.
  - A run cut short can fail but never pass, so the pass counts understate the agent wherever runs are cut short. The summary sets those failures apart.
  - A bump of the pin that recorded a nested agent's tool calls as the agent's own would fail the agent for delegating.
  - Graders of the workspace cannot tell the agent's changes from those of an agent it delegated to, so a nested agent's change counts against the agent.

  The owner and the authors bear these, and can accept them, since a failure is always traceable to the run that produced it, and other levels can run on demand.

### The credential leaves the machine

- **STRIDE threat type**: Information disclosure.
- **Component**: Confined harness.
- **Stakeholders affected**: Owner, and the operator if they supply an API key.
- **Impact**: With the subscription token, whoever holds it can spend the owner's allowance for up to a year. With an API key, they can spend up to any limit the provider enforces, and use any other API that the key reaches, until it is revoked.
- **Attempt likelihood**: Low. This requires code inside the confinement besides Claude Code's and the setup step's, so it depends on the first vector getting past the allowlists, or on a compromised Claude Code release.
- **Method**: Read the credential from the harness's environment, and send it to a host that listens on the proxy's port number. Landlock limits TCP by port only.
- **Mitigations**:
  - The allowlists, as in the first vector.
  - The subscription token grants inference only.
  - The suite never stores an API key.
  - The proxy only relays to allowed hosts, which constrains Claude Code itself.
  - UDP, raw sockets, the operator's runtime sockets, and abstract Unix sockets are denied.
  - The proxy records its refusals, and the summary reports them.
  - It falls to the operator to supply only a standard API key, in a workspace of its own with a spend limit and nothing else in it.
  - Not yet adopted: isolating the confined tree's network in a namespace of its own, which would close the proxy's port to other hosts. On this machine it needs root, so it is the owner's decision.
- **Residual risks**:
  - Code inside the confinement can bypass the proxy for TCP on the proxy's port, at the cost of controlling a listener on that port, which is trivial once the code runs.
  - Revoking the subscription token is unconfirmed.

  The owner bears both, and accepts them with the allowlists in place, unless they adopt the namespace.

### The agent under test acts beyond its workspace

- **STRIDE threat type**: Elevation of privilege.
- **Component**: Runs.
- **Stakeholders affected**: Operator, owner, and anyone that an outward-facing tool could reach.
- **Impact**: The agent could notify, schedule, message, create remote routines, or write outside its workspace.
- **Attempt likelihood**: Medium. Fixtures can contain text that steers the agent, and some cases ask for actions on purpose.
- **Method**: Call a tool that acts beyond the workspace, or one that a new harness version adds.
- **Mitigations**:
  - Runs are only offered tools to read, search, load skills, delegate, and write within the workspace.
  - The tools that act beyond the workspace are disallowed.
  - The tool check voids a harness call in which a run is offered a tool the suite does not expect.
  - The confinement and the proxy apply to everything a run does.
- **Residual risks**: A tool that a new harness version adds, which needs no permission, can be used during the one harness call before the tool check catches it. The owner bears this, and can accept it with a review of every bump of the pin.

### Other processes under the operator's account tamper with the state store or the results

- **STRIDE threat type**: Tampering, and information disclosure.
- **Component**: Operator state store, and invocation temp dir.
- **Stakeholders affected**: Owner.
- **Impact**: A false trust answer, a ledger that understates spend (for example, with a provisional charge removed), a stolen subscription token, or altered results.
- **Attempt likelihood**: Low. It requires one of the operator's other processes to be compromised, or to act on an injected prompt.
- **Method**: Read or write the files directly, as the same user.
- **Mitigations**: None beyond the operating system's user boundary, which does not separate these processes from the suite. The store holds nothing that those processes could not already obtain from the operator's own Claude Code configuration.
- **Residual risks**: The owner bears all of this vector's impact. They accept it, since separating the suite would mean running it under a user account of its own.

### A malicious release of a dependency

- **STRIDE threat type**: Elevation of privilege, and information disclosure.
- **Component**: Confined harness (Claude Code), wrapper (nono), and install-time tooling (npm).
- **Stakeholders affected**: Operator, owner.
- **Impact**:
  - A malicious Claude Code release runs inside the confinement, holding the credential.
  - A malicious nono release can disable the confinement.
  - A malicious npm package runs as the operator at install time.
- **Attempt likelihood**: Low, though such attacks occur in package ecosystems.
- **Method**: Publish a malicious release, and get a bump merged.
- **Mitigations**:
  - Exact pins, with the lockfile's hashes for Claude Code.
  - nono's binary pinned by its hash, which the wrapper checks on every invocation.
  - Version changes only through reviewed pull requests.
  - The confinement around Claude Code.
  - The self-test, which would catch a nono release that stopped confining.
- **Residual risks**: The mitigations fall short in two cases:
  - A malicious nono that passes the self-test whilst failing to confine the real runs.
  - A malicious Claude Code that uses its own permitted access, such as sending the credential through the proxy's port.

  The owner bears both. They are risks of using the tools at all, which the confinement reduces but cannot remove.

### Results or reports leave the machine

- **STRIDE threat type**: Information disclosure.
- **Component**: Confined harness.
- **Stakeholders affected**: Owner.
- **Impact**: Prompts, fixtures, and outputs reach a store or party beyond the model provider.
- **Attempt likelihood**: Low. The harness publishes reports by default, so this only happens if the suite's setting regresses.
- **Method**: Publishing a report, telemetry, or error reporting.
- **Mitigations**:
  - The harness is always told not to publish.
  - Telemetry, error reporting, update checks, and remote feature flags are switched off.
  - The proxy only allows the model API.
- **Residual risks**: The provider keeps prompts and outputs under the terms of the credential used. The owner bears this, and accepts it, since the prompts and fixtures are already public in the repository.
