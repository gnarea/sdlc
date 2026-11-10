# Release notes

When a maintainer pushes a tag that marks a release (e.g., `v2.4.0`), a GitHub Actions workflow drafts the release's notes, so that the maintainer only needs to check them.

## Steps

1. Code lists the pull requests merged since the previous release's tag, with each one's title, description, and labels, and saves them as a JSON file.
2. An agent reads the file and writes the release notes in Markdown, grouping the changes into features, fixes, and breaking changes, in the style of the previous releases' notes.
3. Code checks that the notes mention every pull request in the file, then creates a draft release for the tag, with the notes as its description.
4. A maintainer reads the draft, edits it if needed, and publishes the release.

## Agent

- Model: `claude-sonnet-5-5` at `medium` effort.
- Input: the JSON file of pull requests, and the notes of the last three releases, which code saves beforehand.
- Tools: Read and Write, confined to the job's working directory.
- Identity: none. The agent holds no credentials, and code creates the draft release with the job's `GITHUB_TOKEN`, whose only write permission is `contents: write`.
- Runs: capped at 15 turns and 10 minutes.
