# Agent eval suite

<!-- cspell:words cspell AppArmor Dependabot lockfile seccomp tmpfs worktrees -->

The agent eval suite measures how reliably the `sdlc` plugin's agents behave as their definitions say: whether each agent keeps to its priorities and principles, escalates the hazards it must, stays within its domain, and reviews artefacts and processes feedback as required. Each agent is a Claude Code subagent defined by a prompt and the skills it preloads, so its behaviour can only be observed by running it on a model many times and grading what it did. The suite runs on demand on the operator's Linux machine, through Claude Code's plugin eval harness, on Opus 5.5 at three effort levels. Everything that the harness starts is confined, so that the agents under test cannot reach the operator's files, sockets, or accounts.

```mermaid
flowchart LR
  owner([Owner]) -- "sets the budget, approves the credential" --> operator([Operator])
  operator -- "runs it, confirms trust" --> suite[Agent eval suite]
  suite -- "progress, summary, results" --> operator
  authors([Agent and case authors]) -- "change agents, skills, and cases" --> tree[(Plugin working tree)]
  suite -- "copies when it starts" --> tree
  suite -- "inference, through an egress allowlist" --> provider[(Anthropic model API)]
```

## Purpose

The plugin's agents and skills change often, and agents make many of the changes. A change to a definition or a skill can alter whether an agent loads the skills it must, asks before introducing a hazard, declines work outside its domain, or lets an earlier priority win over a later one. Nobody notices until a caller depends on that behaviour. The owner needs to know, for any working tree and on demand, how often each agent behaves as its definition says, at each effort level that callers use, and at a cost the owner has agreed to.

Each answer must be attributable: a failure must show whether the agent, the case, or the infrastructure was at fault. The measurements must also be extensible, since later suites will test how each agent observes its paired skill (e.g., the programmer and the `programming` skill).

### Non-goals

- Running in CI or on a schedule.
- Measuring adherence to the `escalation` and `artefact-review` skills beyond what the agent definitions require.
- Agent-specific behaviour, which later suites add.
- Keeping results once the machine clears its temporary directory.
- Publishing reports, or sharing results beyond the operator's machine.
- Running on macOS or Windows.
- Testing an agent as a session's main agent, rather than as a delegated subagent. Claude Code does not preload an agent's skills when it starts a session as that agent, and the harness cannot start a session as an agent anyway.

### Deferred decisions

A pilot of one case, with one run per level, settles the following before the full suite is built. Its spend counts against the budget.

- How each run confirms the effort level that the agent under test ran at: from the trace, if it shows it, or else with a dedicated canary case. If neither works, the owner is told that the levels cannot be confirmed, before the full suite is built.
- Whether graders can tell the agent under test's skill loads from those of the session that delegated to it.
- The cost and duration of a run at each level, and the delegating session's share of the cost. The delegating session moves off Opus 5.5 only if that share is material, and if a cheaper model delegates as reliably.
- Whether a minimal model request reports the subscription's weekly utilisation for its long-lived token, since the wrapper's own readings are the budget's only source of it.
- Whether the confined harness needs any host besides the model API.
- The space that a run takes in the temporary directory.

These decisions wait for evidence, or for the owner:

- **Isolating the confined tree's network in a namespace of its own**: This would stop a confined process from reaching another host on the proxy's port. On this machine it needs an AppArmor profile, and therefore root, so it is the owner's decision.
- **Whether a full run fits in the subscription budget**: A full run is 36 cases × 3 levels × 3 runs, or 324 runs. If it does not fit, the owner gets options to trim it before it runs.
- **A confinement policy for macOS**.

### Users and other stakeholders

- **Operator**: Whoever runs the suite on their machine: today the owner, or an agent acting for the owner.
  - Needs: one entry point; a choice of agents and levels, all of them by default; visible progress; a summary per case and level, with inconclusive runs set apart; and a reason whenever the suite refuses to start or stops.
  - Constraints: a Linux machine with Landlock (kernel 7.0); a RAM-backed `/tmp` of 1.9 GB, shared with every session on the machine; and one user account, shared with the owner's other sessions and agents. The operator must also confirm trust in each new worktree in person.
  - Leading alternative: running Claude Code's plugin eval harness directly. That is simpler to set up, works on macOS, and accepts any option. It also leaves the operator's machine within reach of whatever a run executes, has no weekly spending limit, records nothing that ties a result to the code that produced it, and counts infrastructure failures against the agents. On platforms the suite does not support, it is the operator's only option.
  - Trust: the owner trusts the operator with the credential, and therefore with the subscription's allowance or the API key's spend, and with deciding which checkouts may run.
- **Owner**: Signs off the plugin, sets the budget, approves the credential, and is the only one who can unblock the subscription budget after an invocation that could not measure its spend. The owner's constraints are:
  - every subscription eval run, the pilot included, stays within 10% of the weekly allowance;
  - the suite runs on Linux, and Node may be installed for it;
  - for the implementation: the wrapper is written in Python, like the rest of the repo, and confines processes through an official nono library for Python where one does the job, or else through the nono binary. The library does not do the job today, so the binary is used.
- **Agent and case authors**: The people and agents who change agents, skills, cases, or fixtures, including those writing later agent-specific suites.
  - Needs: adding cases next to the existing ones without changing any contract, and results they can attribute.
  - Their changes are untrusted until the operator confirms trust in the checkout. Even then, code they add cannot run unless the suite allows its kind.
  - Leading alternative: trying an agent by hand in their own session. That is cheaper for a single check, but it cannot be repeated or attributed.
- **Other sessions and agents on the owner's account and machine**: They share the subscription's allowance and rate limit, the machine's `/tmp`, the user account, and the configuration of every repository they work in, without having chosen to. The budget caps their loss of the weekly allowance at 10%, plus what the last harness call spends, but caps nothing over a shorter window. The free-space check protects their space in `/tmp`.
- **People who install the plugin**: The marketplace installs the whole repository, so the suite and its fixtures reach every installation. They pay in disk space, and receive whatever the fixtures contain.
- **Anthropic**: Receives every prompt, fixture, and output; serves the runs; and enforces the subscription's allowance or bills the API key.
- **The environment**: Bears the energy cost of every run.

## Principles

### 1. Nothing the suite runs can reach the operator's files, sockets, or accounts, or any host beyond those it needs

The runs carry out a model's choices, on branches that agents may have written, on the machine where the operator's credentials and live sessions are. This optimises for the operator's safety at the expense of setup effort, of portability (Linux only), and of some fidelity: runs cannot use tools that a caller might give an agent, such as a shell or the Web.

### 2. No code runs unless the suite allows its kind

Inside the confinement, only the pinned Claude Code and the one permitted fixture-copying step run. Every other way for a plugin, a case, or a fixture to start code is refused, unless an allowlist names it. The confinement cannot stop a process from sending the credential to an arbitrary host on the proxy's port, so keeping other code from running is what keeps the credential on the machine.

The same holds outside the confinement, for what the wrapper runs on the operator's behalf: nothing that a change, or the configuration of the repository it lives in, names may run. For example, when the wrapper records the code, none of git's filters, hooks, pagers, or external commands may run.

The one exception comes before the wrapper starts. uv, which runs the wrapper, reads the branch's `pyproject.toml` and `uv.lock`, and a branch can use them to make uv build the project, which runs a build backend as the operator. Those two files therefore need the same careful review as the wrapper itself.

The cost is that each new kind of plugin component, case key, or metadata key needs a reviewed change to the suite.

### 3. Spend stays within what was approved, and is checked before it is incurred

On the subscription, all eval invocations together stop once they have raised the week's measured utilisation by 10 points, and only the harness call that crosses that mark can overrun it. With an API key, each invocation stays within a dollar cap that the operator gives, and which has no default. Wherever the reading is uncertain, spend is attributed in the direction that stops the suite earlier, and where spend cannot be measured at all, the suite stops. This optimises for the owner's allowance and money, at the expense of completeness (an invocation can stop between harness calls, and the full set of runs may need trimming) and of availability (an invocation that cannot measure its spend blocks the subscription until the owner clears it).

### 4. Agents are tested the way callers use them

- A main session delegates each case's request to the agent under test, which preloads its skills.
- Both sessions run on Opus 5.5, at the effort level under test.
- The plugin is tested as it stood in the working tree when the invocation started, uncommitted changes included.

This optimises for results that predict real use, at the expense of the delegating session's cost.

One part of real use is conceded. The harness turns remote feature flags off for every run, so the runs use the pinned Claude Code's defaults, whereas the owner's own sessions get flags remotely. Where a flag changes behaviour, the runs can therefore behave differently from the owner's sessions. In exchange, the runs behave the same way on every invocation of a given pin.

### 5. A run counts against an agent only when the agent caused its outcome

A run passes, fails, or is inconclusive. It is inconclusive whenever something other than the agent decided the outcome: the infrastructure, the harness, the confinement, the delegating session, the budget, or an effort level other than the one requested. Rules decide whatever they can, and an LLM judge grades only what rules cannot, from criteria concrete enough to tell a pass from a failure. This optimises for trust in the results, at the expense of coverage: inconclusive runs are reported, not re-run.

### 6. Every result can be traced to what produced it

Each invocation records the code, the versions of the harness and of nono, the models, the effort level, the credential source, and the environment that produced its results. Every harness call of an invocation runs on the same pinned harness, against the same snapshot of the plugin. This optimises for attributing a change in results, at the expense of setup effort (Node, to install the pinned harness) and of trailing the operator's everyday Claude Code.

### 7. The suite adds only what the harness lacks

Claude Code's plugin eval harness already isolates each run, grades it, calls the judge, and caps spend. The suite adds the confinement, the code check, trust, the budget, effort levels, attribution, and the record. This optimises for building and maintaining less, at the expense of being bound to the harness's contracts and to one provider.

## Components

```mermaid
flowchart TB
  operator([Operator]) --> wrapper[Wrapper]
  wrapper <--> store[(Operator state store)]
  wrapper -- "copies when it starts, records its code" --> tree[(Working tree: plugin and cases)]
  wrapper -- "writes" --> snapshot[(Plugin snapshot)]
  wrapper -- "starts once per case and level, with one credential" --> harness
  wrapper -- "takes before each call and after the last" --> reading
  subgraph confined [Confined tree]
    harness[Eval harness: pinned Claude Code] --> runs[Runs: delegating session and agent under test]
    reading[Usage reading: pinned Claude Code]
  end
  harness -- "reads" --> snapshot
  harness -- "writes" --> tmp[(Invocation temp dir)]
  wrapper -- "reads traces, writes manifest and summary" --> tmp
  harness -- "HTTPS" --> proxy[Egress proxy]
  runs -- "HTTPS" --> proxy
  reading -- "HTTPS" --> proxy
  proxy -- "allowed hosts only" --> api[(Anthropic model API)]
```

- **Wrapper**: The suite's only entry point, which the operator runs, unconfined and under the operator's account.
  - It takes the snapshot of the plugin, checks that snapshot, asks the operator to confirm trust, and verifies the confinement.
  - It starts the egress proxy, and starts the confined harness once per case and level, so that each harness call runs one case at one level, and it can check the budget between calls. It runs each case at every requested level before the next case, so that an invocation that stops early still compares the levels on the cases it covered.
  - On the subscription, it takes the usage readings. It enforces spend, classifies every run, and writes the manifest and the summary.
  - It records the code without running anything that the working tree or its repository's configuration names.
  - It knows the credential, the spend ledger, and the trust answers. It trusts the operator, the pinned Claude Code, and the pinned nono.
  - It passes no other options through to the harness, so widening what a run can do takes a reviewed change to the wrapper.
- **Egress proxy**: Runs in the wrapper, unconfined.
  - It relays the confined tree's HTTPS connections to the hosts on its allowlist, on the HTTPS port only, and refuses and records the rest.
  - It also refuses an allowed host whose name resolves to an address that is not public, so that the name cannot be pointed at the machine's own services.
  - TLS runs end to end through it, so it sees the host name, timing, and volume of each connection, and none of the content.
- **Plugin snapshot**: A copy of the plugin's manifest, agents, skills, and cases, which the wrapper takes when the invocation starts, inside the invocation's temp dir. The wrapper's own code is not part of it.
  - The code check checks it, the runs read it, and the manifest records what it holds. What is checked is therefore what runs.
  - Uncommitted changes in the working tree are tested as they stood when the invocation started.
  - It holds no git metadata. For a worktree, that metadata is the main repository's, with every local branch and the shared stash.
- **Confined harness**: Claude Code's plugin eval harness, at the version that the repository pins for its CI validation. It runs inside nono's confinement, which every process it starts inherits.
  - The pin must be at least the first release with a setting for a delegated agent's effort, which came after 2.1.312 and by 2.1.317.
  - Each call runs its case's runs one at a time, grades them, and calls the judge model.
  - Each case runs only with the plugin. The harness's default second set of runs, without the plugin, is turned off, since without the plugin there is no agent under test to delegate to.
  - It holds the credential in its environment, reads the snapshot and the pinned Claude Code, writes only to its call's directory in the invocation's temp dir, and reaches the network only through the proxy. It cannot read the working tree.
  - It gets a home and configuration of its own, fresh for each call, so it shares no state with the operator's Claude Code.
  - Within the confinement, its own isolation of each run still applies: a temporary home and configuration, a filtered environment, the case's graders and other case material out of the agent's reach, no claude.ai connectors, and no published report.
- **Runs**: One Claude Code session per run of a case, made of a main session that delegates the case's request to the agent under test, which preloads its skills. Both use Opus 5.5 at the level under test.
  - Tools: reading and searching the run's workspace and the plugin, loading skills, delegating, and writing within the workspace. A case can withhold writing.
  - Nothing that executes commands, reaches the Web, or acts beyond the workspace.
  - Each run knows only its case's prompt and fixture.
- **Usage reading**: On the subscription, one minimal model request from the pinned Claude Code, whose response reports the seven-day utilisation and the week's reset time.
  - It runs under the same confinement and with the same credential as the harness, and knows nothing else.
  - The wrapper takes one before each harness call, and one after the last.
- **Case suite**: The cases, which sit in the working tree with the plugin.
  - Every agent gets the same kinds of case, each with a scenario in that agent's own domain:
    - review (implied, explicit, and a negative);
    - feedback;
    - domain (and a negative);
    - a confirm-first hazard (and a negative, with the hazard acknowledged up front);
    - priorities.
  - That makes nine cases per agent, 36 in all. Each case is tagged with its agent and runs three times per level.
  - Rules grade what they can: which agent the main session delegated to, whether it passed the case's request on, which session loaded a skill, and whether a fixture file changed. The judge grades the rest.
  - Each run's workspace starts as a copy of its case's fixture. Fixtures hold nothing that looks like a credential, no Claude Code configuration, and no git metadata.
  - Later suites add cases next to these, under the same contracts.
- **Operator state store**: A directory at the account's own `~/.local/state/sdlc-evals`, outside the confinement. The location is fixed whatever the environment says, so that every invocation under the account shares one lock and one ledger. Only the operator's account can read it, and only the wrapper reads it. It holds:
  - the spend ledger, with an entry for each invocation: its credential source and list-price spend and, for the subscription, its first and last readings in each week that its readings touch, keyed by the week's reset time, or a provisional charge whilst a harness call is running. The wrapper deletes entries whose week has reset, except a provisional charge, which stays until the owner clears it;
  - the operator's trust answers, one per worktree, which identify the worktree by its identity on the file system as well as its path, so that a new worktree at an old one's path is asked about afresh. The wrapper deletes an answer once its worktree no longer exists, and asks every time where the file system cannot tell worktrees apart that way;
  - the subscription token, until the operator replaces it or it expires a year after it was issued;
  - the invocation lock, which exists only whilst an invocation holds it.

  The ledger and the trust answers carry a format version from their first release, since later versions of the wrapper must read them. The store holds no API key, and it is not backed up. Its writes are atomic, and each reaches the disk before the wrapper goes on, so a crash or a power cut leaves either the old document or the new one.
- **Invocation temp dir**: One per invocation, under the temporary root (by default the machine's RAM-backed `/tmp`), which only the operator's account can read. The confined tree can write only within it, and only to the directory of the harness call or reading that is running.
  - It holds the plugin snapshot, each run's sandbox until the run's trace is copied, and then the traces, the harness's reports, the manifest, and the summary. The wrapper prints its path.
  - It is kept until the operator deletes it or the machine clears `/tmp`.
- **Working tree**: The plugin under test, the case suite, and the wrapper. The confined tree cannot read it. Nothing the suite writes lands in it, even when the harness is run directly.

### An invocation

1. The operator chooses the agents, the levels, and the credential source. All agents and all levels are the default. The subscription is the default credential; an API key is used only when the operator chooses it and gives a dollar cap.
2. The wrapper takes the operator's invocation lock, which only one invocation at a time can hold under the operator's account. The operating system releases it when the wrapper exits, so a crash cannot leave it behind. If another invocation holds it, the wrapper refuses to start, and names that invocation.
3. The wrapper takes the plugin snapshot, and refuses to start unless each of the following holds:
   - every case uses permitted keys only, which exclude a case-level plugin;
   - every case uses the one permitted fixture-copying step;
   - no fixture holds Claude Code configuration or git metadata;
   - the plugin's root holds only permitted entries;
   - its manifest declares only agents and skills;
   - agent and skill metadata use permitted keys only;
   - no agent or skill embeds a shell command.
4. If the operator has not yet confirmed trust in this worktree, the wrapper asks them at the controlling terminal, before anything runs, so that a process that only controls standard input cannot answer. Only after a yes does the harness treat the plugin as trusted.
5. Before starting, and without any model call, the wrapper checks the confinement from a process two levels below its root, as the runs are. The check must find the following denied:
   - reading the operator's Claude Code configuration and SSH keys;
   - reading the working tree and its repository's git metadata;
   - writing outside the invocation's temp dir;
   - UDP, and TCP to any port but the proxy's;
   - requests through the proxy to hosts that are not on the allowlist;
   - connecting to the sockets in the operator's runtime directory, and to abstract Unix sockets.

   It must find the following allowed: reaching the model API through the proxy, running what the fixture-copying step and the harness's search tool need, and starting the pinned Claude Code. If any check fails, the wrapper refuses to start.
6. For each case in turn, at each requested level in turn:
   - On the subscription, the wrapper takes a reading, and replaces the previous call's provisional charge with the measured charge. If the reading fails, the wrapper stops, or refuses to start if no call has run yet.
   - It checks the spend and the free space, and stops before a harness call that would not fit either. On the subscription, it then records a provisional charge.
   - It starts the confined harness for the case, with the level's effort for both sessions, the call's spend cap, and exactly one credential. Progress reaches the operator as it happens.
   - Afterwards, it stops every process that the call left behind, copies the traces, deletes the sandboxes, classifies the runs, and records the spend.
   - It then compares the tools each run was offered with those the suite expects. If a new tool appeared, it voids the call, names the tool, and stops.
7. On the subscription, the wrapper ends with a reading taken after the last harness call (including after an interruption or a timeout), which replaces the last provisional charge with the measured charge. It then writes the manifest and the summary, releases the lock, and exits with a status.

### Outcomes and records

- **Outcome of a run**: Each run ends up in one of three states.
  - Passed: it completed, and every grader passed.
  - Failed: it completed, and a grader failed.
  - Inconclusive: something other than the agent decided the outcome, and the run is labelled with the cause. The causes are:
    - a harness or API error, a timeout, or the turn limit;
    - a delegation that did not happen as asked, as the trace or the delegation graders show;
    - an effort level other than the requested one;
    - a sandbox denial (a tool result flagged as an error because the confinement refused an operation);
    - a grader that could not run, such as the judge that the harness skips once the spend cap is reached;
    - a run that never ran, or whose harness call's result could not be read;
    - a harness call voided by an unexpected tool.

  Pass counts cover completed runs only. The suite retries nothing itself, since Claude Code already retries API errors with backoff.
- **Summary**: Pass counts per case and level, the inconclusive runs with their causes, how many runs had their effort confirmed, the proxy's refusals, and each level's spend.
- **Manifest**: One per invocation, with a format version. It records:
  - the commit that the snapshot was taken from and, where the snapshot differs from it, the diff of the agents, skills, and suite, untracked files included;
  - the wrapper's own uncommitted changes, including those to `pyproject.toml` and `uv.lock`, untracked files included;
  - the versions of Claude Code and nono, and the model that each run used;
  - the judge model, the effort level, and the credential source (never the credential itself);
  - the environment that was set, and the subset of agents and levels;
  - every utilisation reading that the wrapper took, with its week's reset time, on the subscription;
  - the proxy's refusals and failures to reach an allowed host, and the exit statuses.
- **Exit status**: Distinguishes every case meeting the threshold, a case below it, inconclusive runs, the spend cap, spend that cannot be measured, a refusal to start, and an interruption. This is a contract with whoever calls the wrapper, agents included, so it only changes by addition.

### Spend

- **Subscription**: All eval invocations together, the pilot included, may raise the seven-day utilisation by at most 10 points a week. Only measured utilisation counts: list-price spend is recorded and reported, but plays no part in this budget.
  - The suite's long-lived token cannot read the subscription's usage, so the wrapper takes usage readings of its own: one before each harness call, and one after the last, including after an interruption or a timeout. Every request of the invocation, the judge's included, therefore falls between two readings. The runs' traces carry readings too, but the budget never uses them, so a change in what the traces carry cannot affect it.
  - Readings are in whole percentage points at best, and the owner's other sessions move them too. Attributing all of the change to the evals overestimates their share, so it can only make the suite stop earlier.
  - For each week that an invocation's readings touch, the invocation is charged its last reading in that week minus its first, plus 1 point for the rounding of the two. If the week began during the invocation, its first is taken as zero, since utilisation restarts at the reset. Spend in a week that has already reset counts against nothing.
  - Before each harness call, with that call's fresh reading, the wrapper adds the invocation's charge for the current week to the week's other charges in the ledger, and stops once the total reaches 10 points. The week can therefore exceed 10 points only by what the last call spends, which the next reading records.
  - Each harness call also gets a fixed dollar cap (e.g., $5 for a case's three runs), which bounds a call that goes wrong, whatever the readings show.
  - Before each harness call, the wrapper records a provisional charge for the rest of the week's budget, and replaces it with the measured charge once the next reading is in. A provisional charge does not expire with its week, since a call can run across the reset. If the wrapper dies during a call, or a reading fails, the provisional charge stays, and blocks every subscription invocation until the owner clears it.
  - Only the owner can clear a provisional charge, in person: the wrapper's command for it asks at the controlling terminal, as the trust answer does, and tells the owner to check their usage first. Clearing it leaves the invocation charged what its readings measured before the call that was running.
  - If the first reading fails, the invocation makes no harness call, and exits with the status for spend that cannot be measured. Only that reading's request is spent, and it is not charged. A later reading that fails stops the invocation with the same status.
- **API key**: There is no weekly allowance. The operator gives a dollar cap for the invocation, which has no default, and the wrapper refuses to start without one. It gives each harness call what remains of that cap, and stops once it is spent. A call that is interrupted or times out, or whose result cannot be read, is charged its full cap, since what it spent is unknown.
- **Both**:
  - Only one invocation runs at a time under the operator's account, so two invocations cannot each spend the same remaining budget, even when separate agents start them from different worktrees.
  - Runs go one at a time, which leaves most of the rate limit to the owner's other sessions.
  - The harness checks a call's cap before launching each run, so a call can overrun its cap by at most one run.
  - When a harness call ends, times out, or is interrupted, the wrapper stops every process that the call started, so that no run outlives its call and keeps spending.
  - A new harness version that offers a new tool wastes at most one harness call.

### Failure modes

| Failure | Whose fault | Response |
| --- | --- | --- |
| The code check fails | The change under test | Refuse to start, naming what failed |
| The operator does not confirm trust, or there is no terminal to ask at | The operator's decision | Refuse to start |
| A confinement check fails | The platform or the policy | Refuse to start, naming the check |
| The pinned Claude Code or nono is missing, or nono's binary does not match its pinned hash | The operator's set-up | Refuse to start, saying what to install |
| The state store is unreadable | The infrastructure | Refuse to start, since the budget cannot be checked |
| Another invocation is running | The operator's scheduling | Refuse to start, naming the other invocation |
| A utilisation reading fails | The infrastructure, or the provider | Stop with the status for spend that cannot be measured (before the first harness call, refuse to start), leaving any provisional charge in place |
| The wrapper dies during a harness call | The machine, the operator, or the wrapper | The provisional charge blocks every subscription invocation until the owner clears it in person |
| A provisional charge blocks the subscription | A failed earlier invocation | Refuse to start, saying that the owner must clear it |
| Not enough free space for a harness call | The infrastructure | Stop before that call, keeping earlier calls' results |
| A harness call reaches its dollar cap | The approved budget | The harness stops launching runs and skips the judge; those runs are inconclusive |
| The week's budget, or the API key's cap, is spent | The approved budget | The wrapper stops before the next harness call, with the spend-cap status |
| The model API fails or rate-limits a request | The infrastructure | Claude Code retries with backoff; the run is then inconclusive, and not retried again |
| The proxy refuses a host | The policy (a missing host) or the confined tree | Recorded and reported; a run that fails as a result is inconclusive |
| The confinement refuses an operation in a run | The policy | The run is inconclusive (sandbox denial) |
| A run is offered a tool the suite does not expect | The harness version | The harness call is voided, and the wrapper names the tool and stops |
| The main session does not delegate as asked | The delegating session | The run is inconclusive |
| The agent ran at another effort level | The harness or the account | The run is inconclusive |
| A completed run fails a grader | The agent, or the case | The run fails |
| The harness exits abnormally, times out, or leaves no readable result | The harness | The wrapper stops every process the call started, and the call's unfinished runs are inconclusive; the next reading measures what it spent, or, with an API key, the call is charged its full cap |
| The operator interrupts an invocation | The operator | The wrapper stops every process the call started, takes its last reading (with an API key, charges the call its full cap), records what it has, and stops |

## Dependencies

The suite is coupled to Anthropic on purpose. It exists to test Claude Code agents on Anthropic's models, so none of its layers is meant to be portable. nono is the only replaceable part: any kernel-enforced confinement with the same properties would do.

### Backing services

Only the owner deploys the suite, so these are named by product.

- **Anthropic model API**: Inference for the runs and the judge. With the subscription, it also enforces the weekly allowance, and reports the seven-day utilisation in its responses, on which the subscription budget depends; with an API key, it bills the key. Stakeholders trust it with every prompt, fixture, and output (which hold no personal data beyond what the fixtures contain), and with every run's availability.
- **Anthropic account**: Issues the credential: either an inference-only token, valid for a year and made for unattended jobs, or an API key. That token cannot read the subscription's usage. The account is not contacted during an invocation.

### Delegations

- **Claude Code's plugin eval harness, pinned**: Isolating each run, grading, calling the judge, and capping spend per invocation. Its caveats are:
  - It has no option for effort, for a matrix of levels, or for a main agent, so effort is set through the environment, and each level needs a harness call of its own.
  - It runs each case's setup step as the operator, outside its own sandbox. That is why the confinement and the allowlists exist.
  - It turns non-essential traffic off for every run, which also turns remote feature flags off, so the runs use the pinned version's defaults. It is turned off for the harness too, so that only inference leaves the machine.
  - It reads the plugin's git metadata, which is why the runs get a snapshot without any.
  - It records neither the commit nor the model used.
  - It deletes traces unless told to keep them.
  - By default it publishes its report to claude.ai whenever the account allows it, which a remote flag decides, so the suite always tells it not to.
  - By default it writes results inside the plugin.
  - It skips the judge for a run once the spend cap is reached, and marks that run's LLM graders as failed.
  - Its behaviour changes between patch releases. For example, the setting for a delegated agent's effort first appears in a release after 2.1.312, by 2.1.317. So the version is pinned, only a reviewed change moves it, and the pin must be at least the first release with that setting.
- **Claude Code, running the runs and the usage readings**: Delegation, skill preloading, reporting the utilisation that the API returns, and retrying API errors with backoff. Its caveats are:
  - A remote experiment can lower a delegated agent's effort unless the effort is set explicitly, so it always is.
  - A settings maximum or an organisation cap can lower the effort without saying so, which is why each run must confirm it.
  - Claude Code's own honouring of the proxy settings is the only thing that keeps it to the allowed hosts.
  - Its order of precedence would pick one of two credentials without saying which, so exactly one is passed.
- **nono's binary, through Landlock and seccomp**: Kernel-enforced confinement, which every descendant inherits. Its caveats are:
  - It is used on Linux only, for now.
  - It has not reached version 1.0. It is pinned to an exact release, at least the one that fixes every advisory published before it, and the wrapper checks the binary's hash against the pin on every invocation.
  - Its official library for Python is not used. The library's current release embeds an older nono with unfixed advisories, does not mediate Unix sockets by path (so a confined process could reach the operator's D-Bus session bus), and captures a child's output instead of streaming it.
  - It limits TCP by port only, so the proxy's port is open to every host. Its network-namespace isolation would close that, at the cost described under the deferred decisions.
  - A Unix-socket peer that the policy allowed could hand over a connected socket. The policy allows none.
- **Node and npm**: Installing the pinned Claude Code, verified against the hashes in the repository's lockfile. They are used at install time only, unconfined.
- **git, 2.44 or later**: Recording the commit and the uncommitted changes. git reads the repository's configuration, which every worktree of the repository shares, and which an agent in any of them can change without the change showing in any diff. That configuration can name commands for git to run, such as filters, so the wrapper only uses git commands that run none of them, which need git 2.44 or later.
- **uv**: Running the wrapper, on the Python version that the repository pins. uv reads the branch's `pyproject.toml` and `uv.lock` before the wrapper starts, and a branch can use them to make uv build the project, which runs a build backend as the operator, unconfined. Telling uv not to build does not stop it, so those two files need the same careful review as the wrapper.
- **The operator's Linux machine**: Landlock and seccomp. Its caveats are:
  - `/tmp` is a RAM-backed tmpfs, shared with every session.
  - The suite shares one user account with the owner's other sessions and agents, so no operating-system boundary separates the state store from them.
  - Unprivileged user namespaces are restricted, which is why nono's network-namespace isolation needs an AppArmor profile.
- **Dependabot**: Proposes bumps of the pinned harness as pull requests. A merged bump can bring new tools or components, which the tool check and the allowlists then refuse.

### Hosts contacted

| Host | Contacted by | Why |
| --- | --- | --- |
| Anthropic model API (`api.anthropic.com`) | The harness, the runs, and the usage readings | Inference, for the runs and the judge, and the subscription's utilisation |

Nothing else is contacted during an invocation:

- telemetry, error reporting, update checks, and remote feature flags are switched off;
- claude.ai is never contacted.

Outside any invocation, installing the suite contacts the npm registry, for the pinned Claude Code, and GitHub, for nono's release.

### Legal and contractual obligations

- **Anthropic's terms for the credential used**: For the subscription, these are the consumer terms together with the owner's privacy settings, which decide whether sessions may be used for training, and for how long they are kept. For an API key, they are the commercial terms. The design relies on them for how prompts, fixtures, and outputs are kept and used. If they were breached, what would be exposed is the suite's prompts and fixtures, which the repository already publishes, plus the models' outputs.
- **The subscription's permitted uses**: The design relies on long-lived tokens being meant for unattended jobs, as Claude Code itself describes them. If that changed, subscription runs would fail as inconclusive, and the operator could switch to an API key.

## Relevant standards

- **HTTP CONNECT tunnelling through a proxy ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110#name-connect))**: Adopted for egress. Claude Code honours the conventional proxy settings, and TLS stays end to end, so the proxy sees host names only.
- **[XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/)**: Adopted in part. The operator state store sits at the specification's default state directory, but the wrapper ignores `XDG_STATE_HOME` (and `HOME`), so that a caller's environment cannot give an invocation a lock and a ledger of its own.
- **OAuth 2.0 Token Revocation ([RFC 7009](https://www.rfc-editor.org/rfc/rfc7009))**: Claude Code revokes its own login through such an endpoint, which could serve to revoke the subscription token. Not adopted, since the owner chose not to test whether the endpoint accepts that kind of token.
- **[OpenTelemetry](https://opentelemetry.io/)**: Not adopted. The manifest and the summary are local, and they meet one operator's needs.

## Impact on stakeholders

### Limitations

- **Linux only**: Operators on macOS or Windows bear this. Their workaround is to run the harness directly, without the suite's protections.
- **Slow**: Runs go one at a time, so a full run may take many hours; the pilot measures how many. The operator bears this, and can run a subset of agents or levels instead.
- **One invocation at a time**: Agents acting for the owner in different worktrees must take turns, since the wrapper refuses a second invocation rather than queueing it. They bear this, and can start again once the first invocation ends.
- **The budget only counts invocations under this account on this machine**: Invocations from another machine, or another user account, on the same subscription are missing from the ledger. The owner bears this, and avoids it by running the suite from one machine and account only.
- **The last harness call can take the week past 10%**: The budget is checked before each call, so the call that crosses 10 points runs to its end, within its dollar cap. The owner bears this. The next reading records the excess, so no further invocation runs that week.
- **Each invocation costs at least a point**: The point added for rounding limits the week to ten invocations, however small. The operator bears this, and can cover more agents or levels in each invocation instead.
- **Nothing caps the suite's share of a shorter usage window**: The readings only carry the seven-day window, so a full run can use much of its 10 points in one sitting, leaving less of any shorter window to the owner's other sessions. The owner bears this, and can run the suite in subsets.
- **An invocation that cannot measure its spend blocks the subscription**: If the wrapper dies during a harness call, or a reading fails, no subscription invocation can run until the owner clears the provisional charge in person. The operator and agents acting for the owner bear this, and can use an API key in the meantime.
- **The subscription cannot be used without readings**: If the provider stops reporting the utilisation to the long-lived token, every subscription invocation refuses to start. The owner bears this, and can use an API key instead.
- **Runs use default feature flags**: Behaviour that a remote flag changes in the owner's sessions goes untested. The owner bears this, and there is no workaround, since the harness forces it.
- **Results do not persist**: The machine clears them along with `/tmp`. The operator bears this, and can copy the temp dir before it is cleared.
- **No unattended start in a new worktree**: The operator must confirm trust in person, so an agent cannot start the suite in a new worktree on its own. Where the file system cannot tell worktrees apart beyond their paths, the operator is asked on every invocation. Agents acting for the owner bear this, and there is no workaround.
- **The effort levels might be impossible to confirm**: If the pilot finds no way to confirm them, the owner decides whether the suite is still worth building.
- **Subscription and API-key runs can differ**: The two have different rate limits and caching, which can affect the runs. The manifest records which credential source each invocation used.
- **The full set of runs may not fit the budget**: The owner bears this, and gets options to trim the set before it runs.
- **Revoking the subscription token is unconfirmed**: A token that left the machine might stay valid for up to a year. The owner bears this, and no workaround is confirmed.
- **Losing the state store**: The wrapper would forget this week's eval spend, including any provisional charge, and would ask the operator to confirm trust again. The owner bears the first part, as a budget that could be overrun for the rest of the week.
- **Installations carry the suite**: People who install the plugin get its suite and fixtures, which they do not need. There is no workaround whilst the marketplace installs the whole repository.

### Ethical costs

- **Energy**: Each full run is hundreds of Opus sessions plus judge calls, and everyone bears the cost. Running each case only with the plugin halves it, and running subsets reduces it further. It cannot be removed, because measuring a model's behaviour takes running the model.
- **The owner's shared allowance**: Subscription runs take up to 10% of each week's allowance, plus what the last harness call spends, from the owner's other work and agents, which never chose to share it. The owner chose that limit; the design can only enforce it.
- **Installations**: People who install the plugin carry fixtures they never use. The design cannot avoid this whilst the marketplace installs the whole repository.

### Residual risks

[The threat model](threat-model.md) gives each risk its attack vector, mitigations, and who bears it.

- **The credential can leave the machine through code that the code check misses**: Anything inside the confinement can read the credential from the harness's environment, and send it to any host listening on the proxy's port number. Only the code check keeps other code from running there. Isolating the confined tree's network in a namespace would close this, and is the owner's decision.
  - **Subscription**: The token only grants inference, and lasts a year. If it leaked, whoever held it could spend the owner's allowance until it expired, and revoking it is unconfirmed.
  - **API key**: The key is not limited to inference. If it leaked, whoever held it could spend up to whatever limit the provider enforces on it, and use any other API that the key reaches, until the operator revoked it from the Console. As the operator's own mitigation, the key should be a standard one (never an admin key) in a workspace of its own, with a spend limit and nothing else in it.
- **The wrapper runs unconfined, and sets the confinement policy**: A change to the wrapper, to its allowlists, to the fixture-copying step, or to the `pyproject.toml` and `uv.lock` that uv reads before the wrapper starts can undo every protection here, so each one needs a careful review. So do the commands the wrapper runs, such as git, which must not run anything that the repository's configuration names.
- **Whatever runs in the confinement can read the snapshot**: That is the plugin and its cases, uncommitted changes included. Once committed, they are public anyway.
- **A new harness version can bring new tools or new kinds of component**: The tool check catches a new tool only after a harness call, and an allowlist only refuses what it does not name. A feature that runs code through a key that is already allowed would get through, so every bump of the pin needs a review.
- **The operator's other processes can alter the state store and the results**: They run under the same user account. The store holds nothing that those processes could not already obtain from the operator's own Claude Code configuration.
- **Prompts, fixtures, and outputs are kept by the provider**: This happens under the terms of the credential used.
