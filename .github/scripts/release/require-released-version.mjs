import { requireReleasedPluginVersion } from "./lib/plugin-manifest.mjs";

await requireReleasedPluginVersion(process.cwd(), "HEAD");
