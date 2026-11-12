import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { compareVersions, isVersion } from "./version.mjs";

export const RELEASE_TAG_PREFIX = "v";

const GIT_TIMEOUT_MILLISECONDS = 60_000;

// GitHub's own identity for commits made with a workflow's token.
const ACTIONS_BOT_IDENTITY = {
  GIT_AUTHOR_NAME: "github-actions[bot]",
  GIT_AUTHOR_EMAIL: "41898282+github-actions[bot]@users.noreply.github.com",
  GIT_COMMITTER_NAME: "github-actions[bot]",
  GIT_COMMITTER_EMAIL: "41898282+github-actions[bot]@users.noreply.github.com",
};

const runFile = promisify(execFile);

export async function runGit(repositoryPath, gitArguments, { input } = {}) {
  const child = runFile("git", gitArguments, {
    cwd: repositoryPath,
    timeout: GIT_TIMEOUT_MILLISECONDS,
    env: { ...process.env, ...ACTIONS_BOT_IDENTITY },
  });
  if (input !== undefined) {
    child.child.stdin.end(input);
  }
  const { stdout } = await child;
  return stdout.trim();
}

/** Read the version of the highest release tag reachable from a revision, as semantic-release finds it. */
export async function readLastReleaseVersion(repositoryPath, revision) {
  const tags = await runGit(repositoryPath, ["tag", "--merged", revision, "--list", `${RELEASE_TAG_PREFIX}*`]);
  const versions = tags
    .split("\n")
    .map((tag) => tag.slice(RELEASE_TAG_PREFIX.length))
    .filter(isVersion);
  if (versions.length === 0) {
    throw new Error(`Revision must have a release tag (got none on ${revision})`);
  }
  return versions.sort(compareVersions).at(-1);
}

/**
 * Make the commit that squashing the head onto the base would produce, without touching the working tree.
 *
 * Throws if the head conflicts with the base, since GitHub can't squash it either.
 */
export async function makeSquashCommit(repositoryPath, { baseRevision, headRevision, message }) {
  let tree;
  try {
    tree = await runGit(repositoryPath, ["merge-tree", "--write-tree", "--no-messages", baseRevision, headRevision]);
  } catch (error) {
    throw new Error(`Head must merge into the base without conflicts (got conflicts with ${baseRevision})`, {
      cause: error,
    });
  }
  return runGit(repositoryPath, ["commit-tree", tree, "-p", baseRevision, "-F", "-"], { input: message });
}

export async function listChangedPaths(repositoryPath, fromRevision, toRevision) {
  const paths = await runGit(repositoryPath, ["diff", "--name-only", "--no-renames", fromRevision, toRevision]);
  return paths === "" ? [] : paths.split("\n");
}

export async function isAncestor(repositoryPath, ancestorRevision, descendantRevision) {
  try {
    await runGit(repositoryPath, ["merge-base", "--is-ancestor", ancestorRevision, descendantRevision]);
    return true;
  } catch (error) {
    if (error.code === 1) {
      return false;
    }
    throw error;
  }
}
