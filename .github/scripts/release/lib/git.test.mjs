import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { isAncestor, listChangedPaths, makeSquashCommit, readLastReleaseVersion, runGit } from "./git.mjs";
import { commitEmpty, commitFile, makeRepositoryWithOrigin } from "./testing.mjs";

describe("readLastReleaseVersion", () => {
  test("returns the highest release tag reachable from the revision", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitEmpty(repositoryPath, "First");
    await runGit(repositoryPath, ["tag", "v1.9.0"]);
    await commitEmpty(repositoryPath, "Second");
    await runGit(repositoryPath, ["tag", "v1.10.0"]);
    await runGit(repositoryPath, ["checkout", "--quiet", "-b", "other"]);
    await commitEmpty(repositoryPath, "Unreachable from main");
    await runGit(repositoryPath, ["tag", "v2.0.0"]);

    assert.equal(await readLastReleaseVersion(repositoryPath, "main"), "1.10.0");
  });

  test("ignores tags that aren't releases", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitEmpty(repositoryPath, "First");
    await runGit(repositoryPath, ["tag", "v1.0.0"]);
    await commitEmpty(repositoryPath, "Second");
    for (const tag of ["v1.1", "v1.1.0.0", "v1.1.0-beta.1", "1.2.0", "vnext"]) {
      await runGit(repositoryPath, ["tag", tag]);
    }

    assert.equal(await readLastReleaseVersion(repositoryPath, "HEAD"), "1.0.0");
  });

  test("refuses a revision without releases", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitEmpty(repositoryPath, "Unreleased");
    await runGit(repositoryPath, ["tag", "vnext"]);

    await assert.rejects(readLastReleaseVersion(repositoryPath, "HEAD"), {
      message: "Revision must have a release tag (got none on HEAD)",
    });
  });
});

describe("makeSquashCommit", () => {
  test("makes a commit on the base with the merged tree and the message", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    const baseSha = await commitFile(repositoryPath, { path: "base.md", content: "Base\n", message: "Base" });
    await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
    await commitFile(repositoryPath, { path: "feature.md", content: "Feature\n", message: "Feature" });
    await runGit(repositoryPath, ["checkout", "--quiet", "main"]);
    const movedBaseSha = await commitFile(repositoryPath, { path: "base.md", content: "Moved\n", message: "Move" });

    const squashSha = await makeSquashCommit(repositoryPath, {
      baseRevision: "main",
      headRevision: "feature",
      message: "feat: Add a feature (#7)\n\nWith a description.",
    });

    assert.equal(await runGit(repositoryPath, ["rev-parse", `${squashSha}^`]), movedBaseSha);
    assert.notEqual(movedBaseSha, baseSha);
    assert.equal(await runGit(repositoryPath, ["log", "-1", "--format=%B", squashSha]), "feat: Add a feature (#7)\n\nWith a description.");
    assert.equal(await runGit(repositoryPath, ["show", `${squashSha}:base.md`]), "Moved");
    assert.equal(await runGit(repositoryPath, ["show", `${squashSha}:feature.md`]), "Feature");
    assert.equal(await runGit(repositoryPath, ["rev-parse", "HEAD"]), movedBaseSha);
  });

  test("refuses a head that conflicts with the base", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitFile(repositoryPath, { path: "file.md", content: "Base\n", message: "Base" });
    await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
    await commitFile(repositoryPath, { path: "file.md", content: "Feature\n", message: "Feature" });
    await runGit(repositoryPath, ["checkout", "--quiet", "main"]);
    await commitFile(repositoryPath, { path: "file.md", content: "Main\n", message: "Main" });

    await assert.rejects(
      makeSquashCommit(repositoryPath, { baseRevision: "main", headRevision: "feature", message: "feat: Conflict" }),
      { message: "Head must merge into the base without conflicts (got conflicts with main)" },
    );
  });
});

describe("isAncestor", () => {
  test("says whether a revision is an ancestor of another", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    const firstSha = await commitEmpty(repositoryPath, "First");
    const secondSha = await commitEmpty(repositoryPath, "Second");

    assert.equal(await isAncestor(repositoryPath, firstSha, secondSha), true);
    assert.equal(await isAncestor(repositoryPath, secondSha, firstSha), false);
  });

  test("refuses a revision that doesn't exist", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitEmpty(repositoryPath, "First");

    await assert.rejects(isAncestor(repositoryPath, "v9.9.9", "HEAD"));
  });
});

describe("listChangedPaths", () => {
  test("lists the paths that differ between the revisions", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    const firstSha = await commitFile(repositoryPath, { path: "kept.md", content: "Kept\n", message: "First" });
    await commitFile(repositoryPath, { path: "skills/a/SKILL.md", content: "A\n", message: "Second" });
    await runGit(repositoryPath, ["mv", "kept.md", "moved.md"]);
    await runGit(repositoryPath, ["commit", "--quiet", "--message", "Third"]);

    assert.deepEqual(await listChangedPaths(repositoryPath, firstSha, "HEAD"), ["kept.md", "moved.md", "skills/a/SKILL.md"]);
  });

  test("lists nothing when the revisions have the same tree", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    const firstSha = await commitFile(repositoryPath, { path: "file.md", content: "File\n", message: "First" });
    await commitEmpty(repositoryPath, "Second");

    assert.deepEqual(await listChangedPaths(repositoryPath, firstSha, "HEAD"), []);
  });
});
