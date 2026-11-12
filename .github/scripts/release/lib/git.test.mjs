import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { hasRef, isAncestor, listChangedPaths, makeSquashCommit, mergeTrees, readLastReleaseVersion, runGit } from "./git.mjs";
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
  test("makes a commit on the base with the base's tree and the message", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    const baseSha = await commitFile(repositoryPath, { path: "base.md", content: "Base\n", message: "Base" });

    const squashSha = await makeSquashCommit(repositoryPath, {
      baseRevision: "main",
      message: "feat: Add a feature (#7)\n\nWith a description.",
    });

    assert.equal(await runGit(repositoryPath, ["rev-parse", `${squashSha}^`]), baseSha);
    assert.equal(await runGit(repositoryPath, ["rev-parse", `${squashSha}^{tree}`]), await runGit(repositoryPath, ["rev-parse", `${baseSha}^{tree}`]));
    assert.equal(await runGit(repositoryPath, ["log", "-1", "--format=%B", squashSha]), "feat: Add a feature (#7)\n\nWith a description.");
    assert.equal(await runGit(repositoryPath, ["rev-parse", "HEAD"]), baseSha);
  });
});

describe("mergeTrees", () => {
  async function makeDivergedBranches(t, featureContent) {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitFile(repositoryPath, { path: "file.md", content: "Base\n", message: "Base" });
    await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
    await commitFile(repositoryPath, { path: "other.md", content: "Other\n", message: "Other" });
    await commitFile(repositoryPath, { path: "file.md", content: featureContent, message: "Feature" });
    await runGit(repositoryPath, ["checkout", "--quiet", "main"]);
    await commitFile(repositoryPath, { path: "file.md", content: "Main\n", message: "Main" });
    return repositoryPath;
  }

  test("returns the merged tree when nothing conflicts", async (t) => {
    const repositoryPath = await makeDivergedBranches(t, "Main\n");

    const { tree, conflictedPaths } = await mergeTrees(repositoryPath, "main", "feature");

    assert.deepEqual(conflictedPaths, []);
    assert.equal(await runGit(repositoryPath, ["show", `${tree}:file.md`]), "Main");
    assert.equal(await runGit(repositoryPath, ["show", `${tree}:other.md`]), "Other");
  });

  test("returns the conflicted paths", async (t) => {
    const repositoryPath = await makeDivergedBranches(t, "Feature\n");

    const { tree, conflictedPaths } = await mergeTrees(repositoryPath, "main", "feature");

    assert.deepEqual(conflictedPaths, ["file.md"]);
    assert.equal(await runGit(repositoryPath, ["show", `${tree}:other.md`]), "Other");
  });

  test("refuses a revision that doesn't exist", async (t) => {
    const repositoryPath = await makeDivergedBranches(t, "Feature\n");

    await assert.rejects(mergeTrees(repositoryPath, "main", "missing"));
  });
});

describe("hasRef", () => {
  test("says whether a ref exists", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitEmpty(repositoryPath, "First");
    await runGit(repositoryPath, ["tag", "v1.0.0"]);

    assert.equal(await hasRef(repositoryPath, "refs/tags/v1.0.0"), true);
    assert.equal(await hasRef(repositoryPath, "refs/tags/v2.0.0"), false);
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
  test("lists the paths that the head changed since it diverged from the base", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitFile(repositoryPath, { path: "kept.md", content: "Kept\n", message: "First" });
    await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
    await commitFile(repositoryPath, { path: "skills/a/SKILL.md", content: "A\n", message: "Second" });
    await runGit(repositoryPath, ["mv", "kept.md", "moved.md"]);
    await runGit(repositoryPath, ["commit", "--quiet", "--message", "Third"]);
    await runGit(repositoryPath, ["checkout", "--quiet", "main"]);
    await commitFile(repositoryPath, { path: "main.md", content: "Main\n", message: "Main" });

    assert.deepEqual(await listChangedPaths(repositoryPath, "main", "feature"), ["kept.md", "moved.md", "skills/a/SKILL.md"]);
  });

  test("lists nothing when the head changed nothing", async (t) => {
    const { repositoryPath } = await makeRepositoryWithOrigin(t);
    await commitFile(repositoryPath, { path: "file.md", content: "File\n", message: "First" });
    await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
    await commitEmpty(repositoryPath, "Second");

    assert.deepEqual(await listChangedPaths(repositoryPath, "main", "feature"), []);
  });
});
