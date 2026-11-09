# Issue triage

When someone opens an issue in the Kettle repository, a GitHub Actions workflow runs the triage agent on it, so that maintainers only see issues that are labelled and ready to pick up.

The runner reads the front matter of `agents/triage.md` to set up the session. It then renders the file's body with Jinja2 for the new issue, sends the result as the system prompt, and sends "Triage this issue." as the user prompt.

The front matter's keys are:

- `model` and `effort`: the model that runs the agent, and the effort that it spends.
- `max_turns` and `timeout_seconds`: the caps on each run, which the runner enforces.
- `tools`: the tools that the agent is offered.
- `github_token`: the name of the Actions secret that the runner passes to the tools, which call GitHub's API with it.

The only tool is `add_labels`, which adds two labels to the issue: `type` (`bug`, `feature`, `question`, or `needs-info`) and `area` (`cli`, `api`, `docs`, or `needs-info`). It rejects any other value.
