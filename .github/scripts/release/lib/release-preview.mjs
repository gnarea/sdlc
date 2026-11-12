import { join } from "node:path";
import { pathToFileURL } from "node:url";

import semanticRelease from "semantic-release";

import releaseConfig, { COMMIT_ANALYZER_PLUGIN, RELEASE_NOTES_GENERATOR_PLUGIN } from "../../../../release.config.mjs";
import { RELEASE_TAG_PREFIX, hasRef, listChangedPaths, makeSquashCommit, mergeTrees, runGit } from "./git.mjs";
import { PLUGIN_MANIFEST_PATH, readPluginVersionAt } from "./plugin-manifest.mjs";
import { makeSquashCommitMessage, requireConventionalTitle, requireShortLines } from "./pull-request.mjs";

const [RELEASE_BRANCH] = releaseConfig.branches;

const BASE_REVISION = `origin/${RELEASE_BRANCH}`;

// What Claude Code loads from the plugin, besides the manifest, whose version CI sets.
const LOADED_DIRECTORIES = ["agents/", "skills/"];

export const PreviewOutcome = Object.freeze({
  PREVIEWED: "previewed",
  SUPERSEDED: "superseded",
});

/**
 * Work out what squashing a pull request onto `main` would release, using semantic-release's dry run, and whether
 * the plugin's version has to change for it.
 *
 * The outcome is `SUPERSEDED` if the pull request's head is no longer the commit checked out, since the run for
 * the new head takes over.
 */
export async function previewPullRequest({
  github,
  pullRequestNumber,
  checkedOutSha,
  repositoryPath,
  repositoryUrl,
  workPath,
  log,
}) {
  const pullRequest = await github.readPullRequest(pullRequestNumber);
  if (pullRequest.headSha !== checkedOutSha) {
    return { outcome: PreviewOutcome.SUPERSEDED };
  }
  if (pullRequest.baseBranch !== RELEASE_BRANCH) {
    throw new Error(`Pull request's base must be ${RELEASE_BRANCH} (got ${pullRequest.baseBranch})`);
  }
  requireConventionalTitle(pullRequest.title);
  const squashCommitMessage = makeSquashCommitMessage(pullRequest);
  requireShortLines(squashCommitMessage);

  const releasedVersion = await readPluginVersionAt(repositoryPath, BASE_REVISION);
  const nextRelease = await dryRunRelease({
    repositoryPath,
    repositoryUrl,
    squashCommitMessage,
    releasedVersion,
    workPath,
    log,
  });
  if (nextRelease === null) {
    await requireNothingLoadedChanged(repositoryPath, checkedOutSha, pullRequest.title);
  }

  const expectedVersion = nextRelease?.version ?? releasedVersion;
  const mergedVersion = await readMergedPluginVersion(repositoryPath, checkedOutSha);
  return {
    outcome: PreviewOutcome.PREVIEWED,
    releasedVersion,
    nextRelease,
    versionToBump: mergedVersion === expectedVersion ? null : expectedVersion,
  };
}

/** Summarise a preview in Markdown, for the job's summary. */
export function formatSummary(preview) {
  if (preview.outcome === PreviewOutcome.SUPERSEDED) {
    return "# Release preview\n\nThe pull request's head has moved on, so the run for the new head previews it.\n";
  }

  const { releasedVersion, nextRelease, versionToBump } = preview;
  const bumpNote =
    versionToBump === null ? "" : `\n\nThe version in \`${PLUGIN_MANIFEST_PATH}\` has to change to ${versionToBump}.`;
  if (nextRelease === null) {
    return `# Release preview

Squashing this pull request wouldn't release a new version, so the plugin stays at ${releasedVersion}.${bumpNote}
`;
  }
  return `# Release preview

Squashing this pull request would make a ${nextRelease.type} release, titled \`${nextRelease.name}\`.${bumpNote}

${nextRelease.notes}`;
}

// Existing users only get a change to what Claude Code loads when the version changes.
async function requireNothingLoadedChanged(repositoryPath, headRevision, title) {
  const changedPaths = await listChangedPaths(repositoryPath, BASE_REVISION, headRevision);
  const loadedPaths = changedPaths.filter((path) => LOADED_DIRECTORIES.some((directory) => path.startsWith(directory)));
  if (0 < loadedPaths.length) {
    throw new Error(
      `Pull request changes agents or skills (${loadedPaths.join(", ")}), so its type must release a version, such as feat or fix (got ${JSON.stringify(title)})`,
    );
  }
}

/** Read the plugin's version that merging the head into the base would leave, or null if it conflicts. */
async function readMergedPluginVersion(repositoryPath, headRevision) {
  const { tree, conflictedPaths } = await mergeTrees(repositoryPath, BASE_REVISION, headRevision);
  return conflictedPaths.includes(PLUGIN_MANIFEST_PATH) ? null : readPluginVersionAt(repositoryPath, tree);
}

async function dryRunRelease({ repositoryPath, repositoryUrl, squashCommitMessage, releasedVersion, workPath, log }) {
  const squashCommitSha = await makeSquashCommit(repositoryPath, {
    baseRevision: BASE_REVISION,
    message: squashCommitMessage,
  });
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
  // The pull request's version builds on `main`'s even whilst `main`'s release is running, or after it failed. A
  // failed release on `main` then fails the next one too, until someone repairs it.
  const releasedTag = `${RELEASE_TAG_PREFIX}${releasedVersion}`;
  if (!(await hasRef(remotePath, `refs/tags/${releasedTag}`))) {
    await runGit(remotePath, ["tag", releasedTag, `${squashCommitSha}^`]);
  }
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
  const { type, version, name, notes } = result.nextRelease;
  return { type, version, name, notes };
}
