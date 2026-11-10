# Agent eval suite

The suite checks that the plugin's agents behave as their definitions say. Each case asks a main session to delegate a request to one agent, then grades what the agent did. The wrapper in `runner/` runs Claude Code's plugin eval harness under confinement and within a budget, as [`architecture.md`](architecture.md) and [`threat-model.md`](threat-model.md) describe.

## Setting up

You need Linux with Landlock, and:

- The pinned Claude Code, from `npm ci` at the repository's root.
- [uv](https://docs.astral.sh/uv/) and `/usr/bin/python3`.
- [nono](https://github.com/nolabs-ai/nono) 0.81.0 on your `PATH`, from the release's tarball, since the wrapper refuses any other binary:

  ```shell
  curl -LO https://github.com/nolabs-ai/nono/releases/download/v0.81.0/nono-v0.81.0-aarch64-unknown-linux-gnu.tar.gz
  curl -LO https://github.com/nolabs-ai/nono/releases/download/v0.81.0/SHA256SUMS.txt
  sha256sum --check --ignore-missing SHA256SUMS.txt
  tar -xzf nono-v0.81.0-aarch64-unknown-linux-gnu.tar.gz
  install -m 0755 nono ~/.local/bin/nono
  ```

  On x86-64, use the `x86_64-unknown-linux-gnu` tarball.

Then check the confinement, which makes no model call:

```shell
uv run --locked python -I -B evals/runner self-test
```

## Choosing a credential

- **Subscription** (the default): create a token with `claude setup-token`, then store it with `uv run --locked python -I -B evals/runner store-token`. Paste it, then press Enter twice.
- **API key**: a standard key (never an admin key) in `ANTHROPIC_API_KEY`, with `--credential api-key --max-cost-usd (dollars)`.

On the subscription, all invocations together may raise the weekly usage by 10 points. Each invocation is charged the rise that its own readings of the usage show, plus a point for rounding, so a full run is charged about 2 points.

If the wrapper dies mid-run, it leaves a provisional charge that stops later invocations from starting. Check your usage, then clear it with `uv run --locked python -I -B evals/runner clear-charge`.

## Running it

```shell
uv run --locked python -I -B evals/runner run
```

This runs every case 3 times on Opus 5.5 at low effort, and takes about 1.5 hours. The first time in a worktree, it asks you to confirm that you trust the worktree, so review the change first: anything that runs can read the credential.

These options are repeatable:

- `--agent (agent)` or `--case (agent)/(case)`, for a subset. Name every case you need in one invocation, since each invocation costs at least a point.
- `--level (low, medium, or high)`, for other effort levels.

`--runs (1 to 3)` sets the runs per case. The wrapper prints a short summary and the directory with the details (e.g., `summary.txt`, `manifest.json`, and the traces), which you should delete once you're done.

A run is cut short at its case's time limit (4 minutes at most) or turn limit. It's then inconclusive, unless it already broke a prohibition of the trace (see below), in which case it fails.

| Exit status | Meaning |
| --- | --- |
| 0 | Every run passed. |
| 1 | A case failed. |
| 2 | Some runs were inconclusive. |
| 3 | The budget stopped it early. |
| 4 | It refused to start a case. |
| 5 | It couldn't read the usage. If a case had started, clear the provisional charge once you've checked your usage. |
| 130 | You interrupted it. |

## Writing a case

Copy another case's directory to `evals/(agent)/(case)/`, then change:

- `prompt.md`: the frontmatter (with a `timeout_seconds` of 240 at most), then the preface in `delegation-preface.md` and the request in `<request>` tags.
- `case.yaml`: the case's name.
- `graders/`: the graders, which always include `delegated.md` and `request-passed-on.md`. If either fails, the run is inconclusive.
- `fixture/`: the files that each run starts with, which mustn't include credentials, Claude Code configuration, or git metadata.

Leave `scaffold.sh` as it is. Runs can write to their workspace, unless the case sets `disallowed_tools: [Write, Edit]`.

A `tool_used` grader also counts the delegating session's calls. To check the agent's own calls, use a `regex` grader on the trace that matches lines with a `parent_tool_use_id`. A nested agent's calls aren't in the trace.

A run cut short only fails on a _prohibition of the trace_: a `regex` grader with `target: trace` and `match: not_contains` (with no lookahead), or a `tool_used` grader with `min: 0`. So grade what the agent mustn't do in the trace wherever you can.

## Changing the wrapper

Run its tests with `npm run test:evals`. Every change to the wrapper, its allowlists, `scaffold.sh`, or the Claude Code pin needs a careful review, since the wrapper runs unconfined and sets the confinement's policy.
