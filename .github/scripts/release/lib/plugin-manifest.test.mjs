import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { describe, test } from "node:test";

import { runGit } from "./git.mjs";
import {
  readPluginVersion,
  readPluginVersionAt,
  requireReleasedPluginVersion,
  writePluginVersion,
} from "./plugin-manifest.mjs";
import { commitEmpty, commitPluginVersion, makeRepositoryWithOrigin, makeTemporaryDirectory } from "./testing.mjs";

async function writeManifest(t, manifest) {
  const path = join(await makeTemporaryDirectory(t), "plugin.json");
  await writeFile(path, JSON.stringify(manifest), "utf8");
  return path;
}

describe("readPluginVersion", () => {
  test("returns the manifest's version", async (t) => {
    const manifestPath = await writeManifest(t, { name: "sdlc", version: "1.11.0" });

    assert.equal(await readPluginVersion(manifestPath), "1.11.0");
  });

  const invalidVersions = [
    { name: "a missing version", version: undefined, shown: "undefined" },
    { name: "a version that isn't a string", version: 1, shown: "1" },
    { name: "a partial version", version: "1.11", shown: '"1.11"' },
    { name: "a prefixed version", version: "v1.11.0", shown: '"v1.11.0"' },
  ];

  for (const { name, version, shown } of invalidVersions) {
    test(`refuses ${name}`, async (t) => {
      const manifestPath = await writeManifest(t, { name: "sdlc", version });

      await assert.rejects(readPluginVersion(manifestPath), {
        message: `Plugin manifest's version must be a version (got ${shown})`,
      });
    });
  }
});

describe("readPluginVersionAt", () => {
  test("returns the version at the revision", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    const firstSha = await commitPluginVersion(repositoryPath, "1.11.0", "First");
    await commitPluginVersion(repositoryPath, "1.12.0", "Second");

    assert.equal(await readPluginVersionAt(repositoryPath, firstSha), "1.11.0");
    assert.equal(await readPluginVersionAt(repositoryPath, "HEAD"), "1.12.0");
  });
});

describe("writePluginVersion", () => {
  test("replaces the version, keeping the other fields in place", async (t) => {
    const manifestPath = await writeManifest(t, { name: "sdlc", version: "1.11.0", author: { name: "Gus Narea" } });

    await writePluginVersion(manifestPath, "1.12.0");

    assert.equal(
      await readFile(manifestPath, "utf8"),
      '{\n  "name": "sdlc",\n  "version": "1.12.0",\n  "author": {\n    "name": "Gus Narea"\n  }\n}\n',
    );
  });

  test("refuses anything other than a version", async (t) => {
    const manifestPath = await writeManifest(t, { name: "sdlc", version: "1.11.0" });

    await assert.rejects(writePluginVersion(manifestPath, "1.12.0\nmalicious=true"), {
      message: 'Plugin version must be a version (got "1.12.0\\nmalicious=true")',
    });
    assert.equal(await readPluginVersion(manifestPath), "1.11.0");
  });
});

describe("requireReleasedPluginVersion", () => {
  test("accepts the version of the last release", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitPluginVersion(repositoryPath, "1.11.0", "Release 1.11.0");
    await runGit(repositoryPath, ["tag", "v1.11.0"]);
    await commitEmpty(repositoryPath, "chore: Change nothing that releases");

    await requireReleasedPluginVersion(repositoryPath, "HEAD");
  });

  test("refuses a version that wasn't released", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitPluginVersion(repositoryPath, "1.11.0", "Release 1.11.0");
    await runGit(repositoryPath, ["tag", "v1.11.0"]);
    await commitPluginVersion(repositoryPath, "1.12.0", "chore: Bump without releasing");

    await assert.rejects(requireReleasedPluginVersion(repositoryPath, "HEAD"), {
      message:
        "Plugin's version must be that of the last release (got 1.12.0, last release is 1.11.0): tag the commit that set the plugin's version, and publish its release by hand",
    });
  });

  test("refuses a version lower than the last release's", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitPluginVersion(repositoryPath, "1.12.0", "Release 1.12.0");
    await runGit(repositoryPath, ["tag", "v1.12.0"]);
    await commitPluginVersion(repositoryPath, "1.11.0", "chore: Downgrade");

    await assert.rejects(requireReleasedPluginVersion(repositoryPath, "HEAD"), {
      message: /^Plugin's version must be that of the last release \(got 1\.11\.0, last release is 1\.12\.0\)/,
    });
  });
});
