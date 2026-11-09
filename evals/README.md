# Agent eval suite

The suite measures how reliably the plugin's agents behave as their definitions say. Each case asks a main session to delegate a request to one agent, and grades what the agent did. The wrapper in `runner/` runs Claude Code's plugin eval harness under kernel-enforced confinement, once for each case at each effort level, within the approved budget.

## Setting up

The suite only runs on Linux with Landlock (it's developed on kernel 7.0). It needs:

- The pinned Claude Code: run `npm ci` at the root of the repository.
- [uv](https://docs.astral.sh/uv/), which runs the wrapper on the Python version that `pyproject.toml` pins.
- `/usr/bin/python3`, which runs the confinement self-test inside the confinement.
- [nono](https://github.com/nolabs-ai/nono) 0.81.0 on your `PATH`. The wrapper refuses any other binary, so install the one from the release's tarball:

  ```shell
  curl -LO https://github.com/nolabs-ai/nono/releases/download/v0.81.0/nono-v0.81.0-aarch64-unknown-linux-gnu.tar.gz
  curl -LO https://github.com/nolabs-ai/nono/releases/download/v0.81.0/SHA256SUMS.txt
  sha256sum --check --ignore-missing SHA256SUMS.txt
  tar -xzf nono-v0.81.0-aarch64-unknown-linux-gnu.tar.gz
  install -m 0755 nono ~/.local/bin/nono
  ```

  On x86-64, use the `x86_64-unknown-linux-gnu` tarball instead.

Check the confinement before anything else, without any model call or spend:

```shell
uv run --locked python -I -B evals/runner self-test
```

## Choosing a credential

The wrapper passes exactly one credential to the harness.

- **Subscription** (the default): a long-lived, inference-only token. Create it with `claude setup-token`, then store it with `uv run --locked python -I -B evals/runner store-token`, which reads it without showing it. Paste the whole token, even where a narrow terminal has split it over several lines, then press Enter twice. You can also pipe it in (e.g., from a password manager). The token lasts a year.
- **API key**: a standard key (never an admin key) in `ANTHROPIC_API_KEY`, ideally from a workspace of its own with a spend limit. Pass `--credential api-key --max-cost-usd (dollars)`, since the cap has no default. Each harness call gets what remains of the cap. The wrapper never stores the key.

On the subscription, all eval invocations together may raise the weekly utilisation by 10 points (10% of the weekly allowance). The wrapper reads the utilisation itself, with a small Haiku request, before each harness call and after the last. Each invocation is charged the rise that its readings show, plus a point for rounding, so even a pilot costs a point, and ten invocations at most fit in a week.

Before each harness call, the wrapper records a _provisional charge_ for the rest of the week's budget, and replaces it with the measured charge once the next reading is in. If the wrapper dies during a call, or a reading fails, the provisional charge stays, and every subscription invocation refuses to start. Check your usage, then clear it in person with `uv run --locked python -I -B evals/runner clear-charge`, which asks at your terminal. The invocation stays charged what its readings measured before the call that was running.

## Running it

Run every agent at every level:

```shell
uv run --locked python -I -B evals/runner run
```

The first time you run it in a worktree, it asks you at your terminal to confirm that you trust the worktree. Review the change first: the code check keeps unexpected code from running, but anything that does run can read the credential.

The wrapper starts the harness once for each case at each level. It runs each case at every level before the next, so that an invocation that stops early still compares the levels on the cases it covered.

To run a subset, use `--agent` and `--level` (each repeatable), or `--case (agent)/(case)` with `--runs (1 to 3)`. For example, the pilot runs one case once per level:

```shell
uv run --locked python -I -B evals/runner run --case programmer/review-implied --runs 1
```

The wrapper prints the invocation's directory, which is under `TMPDIR` (by default `/tmp`). It holds `summary.txt`, `manifest.json`, the traces, and the snapshot of the plugin that ran. Copy anything you want to keep, then delete the directory.

The exit status tells you how it went:

| Status | Meaning |
| --- | --- |
| 0 | Every case met the threshold at every level, with no inconclusive run. |
| 1 | A case fell below the threshold at a level. |
| 2 | Some runs were inconclusive, so the results are incomplete. |
| 3 | The spend cap stopped the invocation before every case ran at every level. |
| 4 | The wrapper refused to start, or to start a harness call. |
| 5 | A reading of the weekly utilisation failed, so the spend can't be measured. If no harness call ran, nothing was charged. Otherwise, clear the provisional charge once you've checked your usage. |
| 130 | You interrupted it. |

## Writing a case

Each case is a directory at `evals/(agent)/(case)/`, with:

- `prompt.md`: the frontmatter (`tags`, `runs`, `max_turns`, `timeout_seconds`, `allowed_tools`, and optionally `description` and `disallowed_tools`), then the prompt. The prompt starts with the delegation preface in `delegation-preface.md`, with the agent's name in place of `(agent)`, and puts the request in `<request>` tags.
- `case.yaml`: the case's name and the fixture-copying step. Copy it from another case and change the name.
- `scaffold.sh`: the fixture-copying step, which must be identical in every case. Copy it from another case.
- `graders/`: the graders, which always include `delegated.md` and `request-passed-on.md`. The wrapper counts a run whose delegation graders fail as inconclusive, since the delegating session caused it.
- `fixture/`: the files that each run's workspace starts with. They must not hold anything that looks like a credential, Claude Code configuration, or git metadata.

Every run can write within its workspace, since Write and Edit are granted to the whole invocation. A case that must not write withholds them with `disallowed_tools: [Write, Edit]`.

`tool_used` graders can't tell the agent's tool calls from the delegating session's. To check that the agent itself made a call, use a `regex` grader on the trace, whose lines for the agent's messages carry a `parent_tool_use_id`.

## How the wrapper works

The wrapper refuses to run anything that its allowlists don't name, confines everything the harness starts, and accounts for every harness call's spend. Its modules in `runner/sdlc_evals/` are split by responsibility:

- `cli`, `invocation`, and `invocation_calls`: the command line, the steps of an invocation in order, and its harness calls, until the budget stops them.
- `code_check/`: the allowlists for the plugin and the cases.
- `snapshot` and `working_tree`: the copy of the plugin that an invocation checks and runs, and the record of how it and the wrapper (with `pyproject.toml` and `uv.lock`) differ from their commit, taken without running anything that the repository's configuration names.
- `confinement`, `process_tree`, `self_test`, and `self_test_probe`: the nono policy, stopping everything it confines, and its proof before any run.
- `egress_proxy`: the HTTPS proxy, which only relays to the model API.
- `harness`, `harness_results`, `harness_call`, and `classification`: a harness call's command, what it leaves behind, running it, and each run's outcome.
- `utilisation_reading`: the wrapper's own reading of the weekly utilisation, by the pinned Claude Code under the confinement.
- `spend` and `state/`: the budget, and the operator state store in `~/.local/state/sdlc-evals`, which holds the ledger, the trust answers, the token, and the invocation lock. It ignores `XDG_STATE_HOME` and `HOME`, so that every invocation under the account shares one lock and one ledger.
- `controlling_terminal`: the questions that only the operator can answer, in person, such as trust in a worktree.
- `records` and `exit_status`: the manifest, the summary, and the exit status.

Run its tests with `npm run test:evals`. Every change to the wrapper, its allowlists, the fixture-copying step, or the pinned harness needs a careful review, since the wrapper runs unconfined and sets the confinement's policy.
