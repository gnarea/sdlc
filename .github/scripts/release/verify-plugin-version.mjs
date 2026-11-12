import { join } from "node:path";

import { PLUGIN_MANIFEST_PATH, readPluginVersion } from "./lib/plugin-manifest.mjs";

/** semantic-release plugin that refuses to publish a version other than the one in the plugin's manifest. */
export async function verifyRelease(_pluginConfig, { cwd, nextRelease }) {
  const pluginVersion = await readPluginVersion(join(cwd, PLUGIN_MANIFEST_PATH));
  if (pluginVersion !== nextRelease.version) {
    throw new Error(
      `Plugin's version must be that of the next release (got ${pluginVersion}, expected ${nextRelease.version}): tag the commit that set the plugin's version, and publish its release by hand`,
    );
  }
}
