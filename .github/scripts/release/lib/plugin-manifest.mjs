import { readFile, writeFile } from "node:fs/promises";

import { readLastReleaseVersion, runGit } from "./git.mjs";
import { isVersion } from "./version.mjs";

export const PLUGIN_MANIFEST_PATH = ".claude-plugin/plugin.json";

export async function readPluginVersion(manifestPath) {
  return decodePluginVersion(await readFile(manifestPath, "utf8"));
}

/** Read the plugin's version at a revision (e.g., a branch or a tree) of a repository. */
export async function readPluginVersionAt(repositoryPath, revision) {
  return decodePluginVersion(await runGit(repositoryPath, ["show", `${revision}:${PLUGIN_MANIFEST_PATH}`]));
}

export async function writePluginVersion(manifestPath, version) {
  if (!isVersion(version)) {
    throw new Error(`Plugin version must be a version (got ${JSON.stringify(version)})`);
  }
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  await writeFile(manifestPath, `${JSON.stringify({ ...manifest, version }, null, 2)}\n`, "utf8");
}

function decodePluginVersion(manifestJson) {
  const { version } = JSON.parse(manifestJson);
  if (!isVersion(version)) {
    throw new Error(`Plugin manifest's version must be a version (got ${JSON.stringify(version)})`);
  }
  return version;
}

/**
 * Require the plugin's version to be that of the last release reachable from a revision.
 *
 * Otherwise users would get a version that has no release, or keep one whose changes they don't have.
 */
export async function requireReleasedPluginVersion(repositoryPath, revision) {
  const pluginVersion = await readPluginVersionAt(repositoryPath, revision);
  const lastReleaseVersion = await readLastReleaseVersion(repositoryPath, revision);
  if (pluginVersion !== lastReleaseVersion) {
    throw new Error(
      `Plugin's version must be that of the last release (got ${pluginVersion}, last release is ${lastReleaseVersion}): tag the commit that set the plugin's version, and publish its release by hand`,
    );
  }
}
