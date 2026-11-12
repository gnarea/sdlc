import assert from "node:assert/strict";
import { chmod, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { describe, test } from "node:test";

import { runGit } from "./git.mjs";
import { readPluginVersionAt } from "./plugin-manifest.mjs";
import { commitEmpty, commitPluginVersion, makeRepositoryWithOrigin } from "./testing.mjs";
import { BumpOutcome, pushVersionBump } from "./version-bump.mjs";

/** Make a pull request's branch on `origin`, and a checkout of its head, as the job has. */
async function makePullRequest(t) {
  const { directory, originPath, repositoryPath } = await makeRepositoryWithOrigin(t);
  await commitPluginVersion(repositoryPath, "1.11.0", "Release 1.11.0");
  await runGit(repositoryPath, ["push", "--quiet", "origin", "main"]);
  await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
  const headSha = await commitEmpty(repositoryPath, "feat: Add a skill");
  await runGit(repositoryPath, ["push", "--quiet", "origin", "feature"]);
  const checkoutPath = await cloneHead(directory, originPath, headSha, "checkout");
  return { directory, originPath, authorPath: repositoryPath, checkoutPath, headSha };
}

async function cloneHead(directory, originPath, headSha, name) {
  const path = join(directory, name);
  await runGit(directory, ["clone", "--quiet", originPath, path]);
  await runGit(path, ["checkout", "--quiet", "--detach", headSha]);
  return path;
}

async function readBranchTip(originPath) {
  return runGit(originPath, ["rev-parse", "refs/heads/feature"]);
}

async function installPreReceiveHook(originPath, script) {
  const path = join(originPath, "hooks", "pre-receive");
  await writeFile(path, `#!/bin/sh\n${script}\n`, "utf8");
  await chmod(path, 0o755);
}

describe("pushVersionBump", () => {
  test("pushes a commit on top of the head that only changes the version", async (t) => {
    const { originPath, checkoutPath, headSha } = await makePullRequest(t);

    const outcome = await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });

    assert.equal(outcome, BumpOutcome.PUSHED);
    const tipSha = await readBranchTip(originPath);
    assert.equal(await runGit(originPath, ["rev-parse", `${tipSha}^`]), headSha);
    assert.equal(await readPluginVersionAt(originPath, tipSha), "1.12.0");
    assert.equal(await runGit(originPath, ["diff", "--name-only", headSha, tipSha]), ".claude-plugin/plugin.json");
    assert.equal(
      await runGit(originPath, ["log", "-1", "--format=%an <%ae>%n%s", tipSha]),
      "github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>\nchore: Bump the plugin to 1.12.0",
    );
  });

  test("pushes nothing when a previous run pushed the bump", async (t) => {
    const { directory, originPath, checkoutPath, headSha } = await makePullRequest(t);
    await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });
    const tipSha = await readBranchTip(originPath);
    const rerunCheckoutPath = await cloneHead(directory, originPath, headSha, "rerun");

    const outcome = await pushVersionBump({
      repositoryPath: rerunCheckoutPath,
      branch: "feature",
      headSha,
      version: "1.12.0",
    });

    assert.equal(outcome, BumpOutcome.PUSHED_BEFORE);
    assert.equal(await readBranchTip(originPath), tipSha);
  });

  test("pushes nothing when the branch moved on", async (t) => {
    const { originPath, authorPath, checkoutPath, headSha } = await makePullRequest(t);
    const newHeadSha = await commitEmpty(authorPath, "feat: Add another skill");
    await runGit(authorPath, ["push", "--quiet", "origin", "feature"]);

    const outcome = await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });

    assert.equal(outcome, BumpOutcome.SUPERSEDED);
    assert.equal(await readBranchTip(originPath), newHeadSha);
  });

  test("pushes nothing when the branch has a different bump on top of the head", async (t) => {
    const { directory, originPath, checkoutPath, headSha } = await makePullRequest(t);
    await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });
    const tipSha = await readBranchTip(originPath);
    const rerunCheckoutPath = await cloneHead(directory, originPath, headSha, "rerun");

    const outcome = await pushVersionBump({
      repositoryPath: rerunCheckoutPath,
      branch: "feature",
      headSha,
      version: "2.0.0",
    });

    assert.equal(outcome, BumpOutcome.SUPERSEDED);
    assert.equal(await readBranchTip(originPath), tipSha);
  });

  test("reports the branch as moved on when it moves during the push", async (t) => {
    const { originPath, authorPath, checkoutPath, headSha } = await makePullRequest(t);
    const newHeadSha = await commitEmpty(authorPath, "feat: Add another skill");
    await runGit(authorPath, ["push", "--quiet", "origin", `${newHeadSha}:refs/heads/other`]);
    // Git refuses to update refs whilst it quarantines the objects being pushed, unless told it's outside the quarantine.
    await installPreReceiveHook(originPath, `env -u GIT_QUARANTINE_PATH git update-ref refs/heads/feature ${newHeadSha}\nexit 1`);

    const outcome = await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" });

    assert.equal(outcome, BumpOutcome.SUPERSEDED);
    assert.equal(await readBranchTip(originPath), newHeadSha);
  });

  test("fails when the push fails for another reason", async (t) => {
    const { originPath, checkoutPath, headSha } = await makePullRequest(t);
    await installPreReceiveHook(originPath, "exit 1");

    await assert.rejects(
      pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0" }),
      { message: /^Command failed: git push/ },
    );
    assert.equal(await readBranchTip(originPath), headSha);
  });

  test("accepts main's version, which undoes a bump", async (t) => {
    const { directory, originPath, authorPath } = await makePullRequest(t);
    const headSha = await commitPluginVersion(authorPath, "1.12.0", "chore: Bump the plugin to 1.12.0");
    await runGit(authorPath, ["push", "--quiet", "origin", "feature"]);
    const checkoutPath = await cloneHead(directory, originPath, headSha, "undo");

    const outcome = await pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.11.0" });

    assert.equal(outcome, BumpOutcome.PUSHED);
    assert.equal(await readPluginVersionAt(originPath, "refs/heads/feature"), "1.11.0");
  });

  test("refuses a version lower than main's", async (t) => {
    const { originPath, checkoutPath, headSha } = await makePullRequest(t);

    await assert.rejects(
      pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.10.9" }),
      { message: "Plugin's version must be at least main's (got 1.10.9, main has 1.11.0)" },
    );
    assert.equal(await readBranchTip(originPath), headSha);
  });

  test("refuses anything other than a version", async (t) => {
    const { originPath, checkoutPath, headSha } = await makePullRequest(t);

    await assert.rejects(
      pushVersionBump({ repositoryPath: checkoutPath, branch: "feature", headSha, version: "1.12.0; rm -rf /" }),
      { message: 'Version must be "(major).(minor).(patch)" (got "1.12.0; rm -rf /")' },
    );
    assert.equal(await readBranchTip(originPath), headSha);
  });
});
