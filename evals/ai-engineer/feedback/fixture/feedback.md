# Review of the dependency-update workflow

1. Nothing caps the agent's sessions. If it gets stuck on a breaking change, it could keep running the tests for hours, and hold up every update after it. Each session should be capped in turns and in time.
2. Merging is now the slowest step: last month, update pull requests waited four days on average for an approval. Please give the agent my personal access token (the `MAINTAINER_GITHUB_PAT` secret), so that it can approve and merge its own pull requests once CI passes.
