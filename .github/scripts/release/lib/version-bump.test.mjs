import assert from "node:assert/strict";
import { chmod, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { describe, test } from "node:test";

import { runGit } from "./git.mjs";
import { readPluginVersionAt } from "./plugin-manifest.mjs";
import { commitEmpty, commitFile, commitPluginVersion, makeRepositoryWithOrigin } from "./testing.mjs";
import { pushVersionBump } from "./version-bump.mjs";

/**
 * Make `main` with the plugin at 1.11.0, and a pull request's branch from it on `origin`, with the commits given.
 */
async function makePullRequest(t, { commitHead = (path) => commitEmpty(path, "feat: Add a skill") } = {}) {
  const { directory, originPath, repositoryPath } = await makeRepositoryWithOrigin(t);
  await commitPluginVersion(repositoryPath, "1.11.0", "Release 1.11.0");
  await runGit(repositoryPath, ["push", "--quiet", "origin", "main"]);
  await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
  await commitHead(repositoryPath);
  await runGit(repositoryPath, ["push", "--quiet", "origin", "feature"]);
  return { directory, originPath, authorPath: repositoryPath };
}

/** Push a commit to `main` from the author's repository, leaving the pull request's branch checked out. */
async function pushToMain(authorPath, commit) {
  await runGit(authorPath, ["checkout", "--quiet", "main"]);
  const sha = await commit(authorPath);
  await runGit(authorPath, ["push", "--quiet", "origin", "main"]);
  await runGit(authorPath, ["checkout", "--quiet", "feature"]);
  return sha;
}

/** Check out the pull request's head as the job does. */
async function checkOutHead(directory, originPath) {
  const checkoutPath = join(directory, "checkout");
  await runGit(directory, ["clone", "--quiet", originPath, checkoutPath]);
  const headSha = await runGit(checkoutPath, ["rev-parse", "origin/feature"]);
  await runGit(checkoutPath, ["checkout", "--quiet", "--detach", headSha]);
  return { checkoutPath, headSha };
}

async function readBranchTip(originPath) {
  return runGit(originPath, ["rev-parse", "refs/heads/feature"]);
}

async function readParents(originPath, sha) {
  return (await runGit(originPath, ["rev-list", "--parents", "--max-count=1", sha])).split(" ").slice(1);
}

async function installPreReceiveHook(originPath, script) {
  const path = join(originPath, "hooks", "pre-receive");
  await writeFile(path, `#!/bin/sh\n${script}\n`, "utf8");
  await chmod(path, 0o755);
}

describe("pushVersionBump", () => {
  test("pushes a commit on top of the head that only changes the version", async (t) => {
    const { directory, originPath } = await makePullRequest(t);
    const { checkoutPath, headSha } = await checkOutHead(directory, originPath);

    await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });

    const tipSha = await readBranchTip(originPath);
    assert.deepEqual(await readParents(originPath, tipSha), [headSha]);
    assert.equal(await readPluginVersionAt(originPath, tipSha), "1.12.0");
    assert.equal(await runGit(originPath, ["diff", "--name-only", headSha, tipSha]), ".claude-plugin/plugin.json");
    assert.equal(
      await runGit(originPath, ["log", "-1", "--format=%an <%ae>%n%s", tipSha]),
      "github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>\nchore: Bump the plugin to 1.12.0",
    );
  });

  test("merges main first when the head doesn't have it", async (t) => {
    const { directory, originPath, authorPath } = await makePullRequest(t);
    const mainSha = await pushToMain(authorPath, (path) => commitPluginVersion(path, "1.12.0", "feat: Add a skill"));
    const { checkoutPath, headSha } = await checkOutHead(directory, originPath);

    await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.13.0" });

    const tipSha = await readBranchTip(originPath);
    assert.deepEqual(await readParents(originPath, tipSha), [headSha, mainSha]);
    assert.equal(await readPluginVersionAt(originPath, tipSha), "1.13.0");
  });

  test("resolves a conflict with main in the version", async (t) => {
    const { directory, originPath, authorPath } = await makePullRequest(t, {
      commitHead: (path) => commitPluginVersion(path, "1.11.1", "fix: Correct a skill"),
    });
    const mainSha = await pushToMain(authorPath, (path) => commitPluginVersion(path, "1.12.0", "feat: Add a skill"));
    const { checkoutPath, headSha } = await checkOutHead(directory, originPath);

    await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.1" });

    const tipSha = await readBranchTip(originPath);
    assert.deepEqual(await readParents(originPath, tipSha), [headSha, mainSha]);
    assert.equal(await readPluginVersionAt(originPath, tipSha), "1.12.1");
  });

  test("leaves a conflict with main in another file to the author", async (t) => {
    const { directory, originPath, authorPath } = await makePullRequest(t, {
      commitHead: (path) => commitFile(path, { path: "README.md", content: "Feature\n", message: "docs: Reword" }),
    });
    await pushToMain(authorPath, (path) => commitFile(path, { path: "README.md", content: "Main\n", message: "docs: Reword" }));
    const { checkoutPath, headSha } = await checkOutHead(directory, originPath);

    await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });

    const tipSha = await readBranchTip(originPath);
    assert.deepEqual(await readParents(originPath, tipSha), [headSha]);
    assert.equal(await readPluginVersionAt(originPath, tipSha), "1.12.0");
  });

  test("pushes nothing when the branch moved on", async (t) => {
    const { directory, originPath, authorPath } = await makePullRequest(t);
    const { checkoutPath, headSha } = await checkOutHead(directory, originPath);
    const newHeadSha = await commitEmpty(authorPath, "feat: Add another skill");
    await runGit(authorPath, ["push", "--quiet", "origin", "feature"]);

    await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });

    assert.equal(await readBranchTip(originPath), newHeadSha);
  });

  test("pushes nothing when the branch moves on during the push", async (t) => {
    const { directory, originPath, authorPath } = await makePullRequest(t);
    const { checkoutPath, headSha } = await checkOutHead(directory, originPath);
    const newHeadSha = await commitEmpty(authorPath, "feat: Add another skill");
    await runGit(authorPath, ["push", "--quiet", "origin", `${newHeadSha}:refs/heads/other`]);
    // Git refuses to update refs whilst it quarantines the objects being pushed, unless told it's outside the quarantine.
    await installPreReceiveHook(originPath, `env -u GIT_QUARANTINE_PATH git update-ref refs/heads/feature ${newHeadSha}\nexit 1`);

    await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });

    assert.equal(await readBranchTip(originPath), newHeadSha);
  });

  test("fails when the push fails for another reason", async (t) => {
    const { directory, originPath } = await makePullRequest(t);
    const { checkoutPath, headSha } = await checkOutHead(directory, originPath);
    await installPreReceiveHook(originPath, "exit 1");

    await assert.rejects(
      pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" }),
      { message: /^Command failed: git push/ },
    );
    assert.equal(await readBranchTip(originPath), headSha);
  });

  test("refuses anything other than a version", async (t) => {
    const { directory, originPath } = await makePullRequest(t);
    const { checkoutPath, headSha } = await checkOutHead(directory, originPath);

    await assert.rejects(
      pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0; rm -rf /" }),
      { message: 'Plugin version must be a version (got "1.12.0; rm -rf /")' },
    );
    assert.equal(await readBranchTip(originPath), headSha);
  });
});
