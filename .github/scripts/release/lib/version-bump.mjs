import { join } from "node:path";

import { runGit } from "./git.mjs";
import { PLUGIN_MANIFEST_PATH, readPluginVersionAt, writePluginVersion } from "./plugin-manifest.mjs";
import { compareVersions } from "./version.mjs";

const BASE_REVISION = "origin/main";

export const BumpOutcome = Object.freeze({
  PUSHED: "pushed",
  PUSHED_BEFORE: "pushed-before",
  SUPERSEDED: "superseded",
});

/**
 * Commit a new version of the plugin on top of a pull request's head, and push it to the pull request's branch.
 *
 * It's safe to repeat: if the branch already has the bump on top of that head (e.g., a previous run died before
 * finishing), it pushes nothing. If the branch moved on otherwise, the bump is left to the run for its new head.
 */
export async function pushVersionBump({ repositoryPath, branch, headSha, version }) {
  const baseVersion = await readPluginVersionAt(repositoryPath, BASE_REVISION);
  if (compareVersions(version, baseVersion) < 0) {
    throw new Error(`Plugin's version must be at least main's (got ${version}, main has ${baseVersion})`);
  }

  const tipSha = await readBranchTip(repositoryPath, branch);
  if (tipSha !== headSha) {
    return describeMovedBranch(repositoryPath, { tipSha, headSha, version });
  }

  await runGit(repositoryPath, ["checkout", "--quiet", "--detach", headSha]);
  await writePluginVersion(join(repositoryPath, PLUGIN_MANIFEST_PATH), version);
  await runGit(repositoryPath, ["commit", "--quiet", "--message", `chore: Bump the plugin to ${version}`, "--", PLUGIN_MANIFEST_PATH]);
  try {
    await runGit(repositoryPath, ["push", "--quiet", "origin", `HEAD:refs/heads/${branch}`]);
  } catch (error) {
    const newTipSha = await readBranchTip(repositoryPath, branch);
    if (newTipSha === headSha) {
      throw error;
    }
    return describeMovedBranch(repositoryPath, { tipSha: newTipSha, headSha, version });
  }
  return BumpOutcome.PUSHED;
}

async function readBranchTip(repositoryPath, branch) {
  await runGit(repositoryPath, ["fetch", "--quiet", "origin", `refs/heads/${branch}`]);
  return runGit(repositoryPath, ["rev-parse", "FETCH_HEAD"]);
}

async function describeMovedBranch(repositoryPath, { tipSha, headSha, version }) {
  const parentShas = (await runGit(repositoryPath, ["rev-list", "--parents", "--max-count=1", tipSha])).split(" ").slice(1);
  const isBumpOfHead =
    parentShas.length === 1 &&
    parentShas[0] === headSha &&
    (await readPluginVersionAt(repositoryPath, tipSha)) === version;
  return isBumpOfHead ? BumpOutcome.PUSHED_BEFORE : BumpOutcome.SUPERSEDED;
}
