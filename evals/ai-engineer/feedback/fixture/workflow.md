# Dependency updates

Every Monday, a GitHub Actions workflow updates the project's npm dependencies, one package at a time, and opens a pull request for each update, so that maintainers only need to review and merge them.

## Steps

1. Code runs `npm outdated --json` to list the packages that have a newer version.
2. For each package, code creates a fresh container with the repository checked out on a new branch, runs `npm install (package)@(version)` in it, and downloads the release notes of every version since the current one.
3. An agent reads the release notes, adapts the code to any breaking change, and runs the tests until they pass. It ends with a summary of what changed and why.
4. Code commits the changes, pushes the branch, and opens a pull request as the `deps-bot` GitHub App, with the agent's summary as its description.
5. CI runs the tests on the pull request, without access to any secret. A branch ruleset on `main` blocks the merge until a maintainer approves it.

## Agent

- Model: `claude-sonnet-5-5` at `medium` effort, since the task is well defined.
- Prompts: a system prompt that describes the task, and a user prompt that names the package, its current and new versions, and the paths to the release notes.
- Tools: Read, Edit, Write, and Bash.
- Confinement: the container holds only the checkout and the release notes, has no credentials, and can only reach the npm registry.
