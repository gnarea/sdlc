import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { template } from "lodash-es";
import semanticRelease from "semantic-release";

import releaseConfig, {
  COMMIT_ANALYZER_PLUGIN,
  RELEASE_BODY_TEMPLATE,
  RELEASE_NAME_TEMPLATE,
  RELEASE_NOTES_GENERATOR_PLUGIN,
} from "../../../../release.config.mjs";
import { RELEASE_TAG_PREFIX, isAncestor, listChangedPaths, makeSquashCommit, runGit } from "./git.mjs";
import { waitForRelease } from "./github.mjs";
import { PLUGIN_MANIFEST_PATH, readPluginVersionAt } from "./plugin-manifest.mjs";
import { makeSquashCommitMessage, requireConventionalTitle, requireShortLines } from "./pull-request.mjs";

const [RELEASE_BRANCH] = releaseConfig.branches;

const BASE_REVISION = `origin/${RELEASE_BRANCH}`;

// What Claude Code loads from the plugin, besides the manifest, whose version CI sets.
const LOADED_DIRECTORIES = ["agents/", "skills/"];

/**
 * Work out what squashing a pull request onto `main` would release, using semantic-release's dry run.
 *
 * Waits for `main`'s own version to be released first, since the version of the pull request builds on it.
 */
export async function previewPullRequest({
  github,
  pullRequestNumber,
  checkedOutSha,
  repositoryPath,
  repositoryUrl,
  workPath,
  log,
  clock,
}) {
  const pullRequest = await github.readPullRequest(pullRequestNumber);
  if (pullRequest.baseBranch !== RELEASE_BRANCH) {
    throw new Error(`Pull request's base must be ${RELEASE_BRANCH} (got ${pullRequest.baseBranch})`);
  }
  if (pullRequest.headSha !== checkedOutSha) {
    throw new Error(
      `Pull request's head must be the commit checked out (got ${pullRequest.headSha}, expected ${checkedOutSha}): the run for its head takes over`,
    );
  }
  requireConventionalTitle(pullRequest.title);
  const squashCommitMessage = makeSquashCommitMessage(pullRequest);
  requireShortLines(squashCommitMessage);

  const releasedVersion = await readPluginVersionAt(repositoryPath, BASE_REVISION);
  await requireRelease(github, repositoryPath, `${RELEASE_TAG_PREFIX}${releasedVersion}`, clock);

  const squashCommitSha = await makeSquashCommit(repositoryPath, {
    baseRevision: BASE_REVISION,
    headRevision: checkedOutSha,
    message: squashCommitMessage,
  });
  const nextRelease = await dryRunRelease({ repositoryPath, repositoryUrl, squashCommitSha, workPath, log });
  if (nextRelease === null) {
    await requireNothingLoadedChanged(repositoryPath, squashCommitSha, pullRequest.title);
  }
  return {
    releasedVersion,
    nextRelease,
    pluginVersion: await readPluginVersionAt(repositoryPath, squashCommitSha),
    expectedPluginVersion: nextRelease?.version ?? releasedVersion,
  };
}

/** Summarise a preview in Markdown, for the job's summary. */
export function formatSummary({ releasedVersion, nextRelease }) {
  if (nextRelease === null) {
    return `# Release preview

Squashing this pull request wouldn't release a new version, so \`${PLUGIN_MANIFEST_PATH}\` must keep version ${releasedVersion}.
`;
  }
  return `# Release preview

Squashing this pull request would make a ${nextRelease.type} release, so \`${PLUGIN_MANIFEST_PATH}\` must have version ${nextRelease.version}.

The release would be titled \`${nextRelease.name}\`, with these notes:

${nextRelease.body}`;
}

async function requireRelease(github, repositoryPath, tag, clock) {
  await waitForRelease(github, tag, clock);
  await runGit(repositoryPath, ["fetch", "--quiet", "origin", `refs/tags/${tag}:refs/tags/${tag}`]);
  if (!(await isAncestor(repositoryPath, tag, BASE_REVISION))) {
    throw new Error(`Release ${tag} must be on ${RELEASE_BRANCH} (got a tag that isn't)`);
  }
}

// Existing users only get a change to what Claude Code loads when the version changes.
async function requireNothingLoadedChanged(repositoryPath, squashCommitSha, title) {
  const changedPaths = await listChangedPaths(repositoryPath, BASE_REVISION, squashCommitSha);
  const loadedPaths = changedPaths.filter((path) => LOADED_DIRECTORIES.some((directory) => path.startsWith(directory)));
  if (0 < loadedPaths.length) {
    throw new Error(
      `Pull request changes agents or skills (${loadedPaths.join(", ")}), so its type must release a version (got ${JSON.stringify(title)})`,
    );
  }
}

async function dryRunRelease({ repositoryPath, repositoryUrl, squashCommitSha, workPath, log }) {
  const remotePath = join(workPath, "remote.git");
  const clonePath = join(workPath, "clone");
  await runGit(workPath, ["init", "--quiet", "--bare", `--initial-branch=${RELEASE_BRANCH}`, remotePath]);
  await runGit(repositoryPath, [
    "push",
    "--quiet",
    remotePath,
    `${squashCommitSha}:refs/heads/${RELEASE_BRANCH}`,
    "refs/tags/*:refs/tags/*",
  ]);
  await runGit(workPath, ["clone", "--quiet", "--branch", RELEASE_BRANCH, remotePath, clonePath]);
  // The release notes link to the repository at the URL that semantic-release uses, so git has to resolve GitHub's
  // URL to the local copy, which has the squash commit and needs no credentials.
  await runGit(clonePath, ["config", `url.${pathToFileURL(remotePath)}.insteadOf`, repositoryUrl]);

  const result = await semanticRelease(
    {
      branches: releaseConfig.branches,
      repositoryUrl,
      plugins: [COMMIT_ANALYZER_PLUGIN, RELEASE_NOTES_GENERATOR_PLUGIN],
      dryRun: true,
      ci: false,
    },
    { cwd: clonePath, env: { PATH: process.env.PATH, HOME: process.env.HOME }, stdout: log, stderr: log },
  );
  if (result === false) {
    return null;
  }

  const templateContext = { branch: { name: RELEASE_BRANCH }, lastRelease: result.lastRelease, nextRelease: result.nextRelease };
  return {
    type: result.nextRelease.type,
    version: result.nextRelease.version,
    name: template(RELEASE_NAME_TEMPLATE)(templateContext),
    body: template(RELEASE_BODY_TEMPLATE)(templateContext),
  };
}
