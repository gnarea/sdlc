import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { isVersion } from "./version.mjs";

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
  const tags = await runGit(repositoryPath, [
    "tag",
    "--merged",
    revision,
    "--list",
    `${RELEASE_TAG_PREFIX}*`,
    "--sort=-version:refname",
  ]);
  const version = tags
    .split("\n")
    .map((tag) => tag.slice(RELEASE_TAG_PREFIX.length))
    .find(isVersion);
  if (version === undefined) {
    throw new Error(`Revision must have a release tag (got none on ${revision})`);
  }
  return version;
}

export async function hasRef(repositoryPath, ref) {
  try {
    await runGit(repositoryPath, ["rev-parse", "--verify", "--quiet", ref]);
    return true;
  } catch (error) {
    if (error.code === 1) {
      return false;
    }
    throw error;
  }
}

/**
 * Make a commit on the base with the message that squashing a pull request would give it.
 *
 * It keeps the base's tree, since semantic-release only reads the messages.
 */
export async function makeSquashCommit(repositoryPath, { baseRevision, message }) {
  return runGit(repositoryPath, ["commit-tree", `${baseRevision}^{tree}`, "-p", baseRevision, "-F", "-"], {
    input: message,
  });
}

/**
 * Merge the head into the base without touching the working tree, returning the merged tree and any conflicted paths.
 *
 * The tree has conflict markers in the conflicted paths.
 */
export async function mergeTrees(repositoryPath, baseRevision, headRevision) {
  const mergeArguments = ["merge-tree", "--write-tree", "--name-only", "--no-messages", baseRevision, headRevision];
  let output;
  try {
    output = await runGit(repositoryPath, mergeArguments);
  } catch (error) {
    // Git also exits with 1 when it can't merge at all (e.g., a revision is missing), but then it writes no tree.
    if (error.code !== 1 || error.stdout.trim() === "") {
      throw error;
    }
    output = error.stdout.trim();
  }
  const [tree, ...conflictedPaths] = output.split("\n");
  return { tree, conflictedPaths };
}

/** List the paths that the head changed since it diverged from the base. */
export async function listChangedPaths(repositoryPath, baseRevision, headRevision) {
  const paths = await runGit(repositoryPath, ["diff", "--name-only", "--no-renames", `${baseRevision}...${headRevision}`]);
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
