import { appendFile, mkdtemp } from "node:fs/promises";
import { join } from "node:path";

import { readEnvironmentVariable, readPullRequestNumber } from "./lib/environment.mjs";
import { makeGitHubClient } from "./lib/github.mjs";
import { formatSummary, previewPullRequest } from "./lib/release-preview.mjs";

const repository = readEnvironmentVariable("GITHUB_REPOSITORY");
const preview = await previewPullRequest({
  github: makeGitHubClient({ repository, token: readEnvironmentVariable("GITHUB_TOKEN") }),
  pullRequestNumber: readPullRequestNumber("PULL_REQUEST_NUMBER"),
  checkedOutSha: readEnvironmentVariable("CHECKED_OUT_SHA"),
  repositoryPath: process.cwd(),
  repositoryUrl: `${readEnvironmentVariable("GITHUB_SERVER_URL")}/${repository}.git`,
  workPath: await mkdtemp(join(readEnvironmentVariable("RUNNER_TEMP"), "release-preview-")),
  log: process.stdout,
});

await appendFile(readEnvironmentVariable("GITHUB_STEP_SUMMARY"), formatSummary(preview), "utf8");
await appendFile(readEnvironmentVariable("GITHUB_OUTPUT"), `version-to-bump=${preview.versionToBump ?? ""}\n`, "utf8");
