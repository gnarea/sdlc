import { join } from "node:path";

import { isAncestor, runGit } from "./git.mjs";
import { PLUGIN_MANIFEST_PATH, writePluginVersion } from "./plugin-manifest.mjs";

const BASE_REVISION = "origin/main";

/**
 * Set the plugin's version on top of a pull request's head, and push it to the pull request's branch.
 *
 * It merges `main` into the head first, unless the head has it already, so that the version can't conflict with
 * `main`'s later. A conflict in any other file is left for the pull request's author to resolve.
 *
 * It pushes nothing if the branch has moved on from the head, since the run for the new head takes over.
 */
export async function pushVersionBump({ repositoryPath, branch, headSha, version }) {
  if ((await readBranchTip(repositoryPath, branch)) !== headSha) {
    return;
  }

  await runGit(repositoryPath, ["checkout", "--quiet", "--detach", headSha]);
  if (!(await isAncestor(repositoryPath, BASE_REVISION, headSha))) {
    await mergeBase(repositoryPath);
  }
  await writePluginVersion(join(repositoryPath, PLUGIN_MANIFEST_PATH), version);
  await runGit(repositoryPath, ["add", "--", PLUGIN_MANIFEST_PATH]);
  await runGit(repositoryPath, ["commit", "--quiet", "--message", `chore: Bump the plugin to ${version}`]);
  try {
    await runGit(repositoryPath, ["push", "--quiet", "origin", `HEAD:refs/heads/${branch}`]);
  } catch (error) {
    if ((await readBranchTip(repositoryPath, branch)) === headSha) {
      throw error;
    }
  }
}

async function mergeBase(repositoryPath) {
  try {
    await runGit(repositoryPath, ["merge", "--quiet", "--no-ff", "--no-commit", BASE_REVISION]);
  } catch (error) {
    const conflictedPaths = await runGit(repositoryPath, ["diff", "--name-only", "--diff-filter=U"]);
    if (conflictedPaths === "") {
      throw error;
    }
    if (conflictedPaths === PLUGIN_MANIFEST_PATH) {
      // Take main's manifest, since its version is about to be replaced.
      await runGit(repositoryPath, ["checkout", "--theirs", "--", PLUGIN_MANIFEST_PATH]);
    } else {
      await runGit(repositoryPath, ["merge", "--abort"]);
    }
  }
}

async function readBranchTip(repositoryPath, branch) {
  await runGit(repositoryPath, ["fetch", "--quiet", "origin", `refs/heads/${branch}`]);
  return runGit(repositoryPath, ["rev-parse", "FETCH_HEAD"]);
}
