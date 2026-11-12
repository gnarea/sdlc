import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { commitPluginVersion, makeRepositoryWithOrigin } from "./lib/testing.mjs";
import { verifyRelease } from "./verify-plugin-version.mjs";

describe("verifyRelease", () => {
  test("accepts the version in the manifest", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitPluginVersion(repositoryPath, "1.12.0", "feat: Add a skill");

    await verifyRelease({}, { cwd: repositoryPath, nextRelease: { version: "1.12.0" } });
  });

  test("refuses any other version", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitPluginVersion(repositoryPath, "1.12.0", "feat: Add a skill");

    await assert.rejects(verifyRelease({}, { cwd: repositoryPath, nextRelease: { version: "1.11.1" } }), {
      message:
        "Plugin's version must be that of the next release (got 1.12.0, expected 1.11.1): tag the commit that set the plugin's version, and publish its release by hand",
    });
  });
});
