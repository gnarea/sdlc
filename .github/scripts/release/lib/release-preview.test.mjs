import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { Writable } from "node:stream";
import { describe, test } from "node:test";

import { runGit } from "./git.mjs";
import { formatSummary, previewPullRequest } from "./release-preview.mjs";
import { commitEmpty, commitFile, commitPluginVersion, makeRepositoryWithOrigin } from "./testing.mjs";

const REPOSITORY_URL = "https://github.com/gnarea/sdlc.git";

const NULL_LOG = new Writable({ write: (_chunk, _encoding, callback) => callback() });

/** Fake of GitHub that serves one pull request, and has the releases given. */
function makeFakeGitHub({ pullRequest, releaseTags }) {
  const readNumbers = [];
  return {
    readNumbers,
    async readPullRequest(number) {
      readNumbers.push(number);
      return { number, ...pullRequest };
    },
    async hasRelease(tag) {
      return releaseTags.includes(tag);
    },
  };
}

/** Fake clock whose sleeps advance its time straight away. */
function makeFakeClock() {
  let time = 0;
  return { now: () => time, sleep: async (milliseconds) => void (time += milliseconds) };
}

/**
 * Make a repository whose `main` released 1.11.0, plus a pull request's head with the commits given, checked out
 * as the job has it.
 */
async function makePullRequest(t, { commitHead = (path) => commitEmpty(path, "Change") } = {}) {
  const { directory, repositoryPath } = await makeRepositoryWithOrigin(t);
  await commitPluginVersion(repositoryPath, "1.11.0", "Release sdlc 1.11.0 (#62)");
  await runGit(repositoryPath, ["tag", "v1.11.0"]);
  await commitEmpty(repositoryPath, "Add an unconventional change (#70)");
  await runGit(repositoryPath, ["push", "--quiet", "--tags", "origin", "main"]);
  await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
  const headSha = await commitHead(repositoryPath);
  await runGit(repositoryPath, ["push", "--quiet", "origin", "feature"]);
  await runGit(repositoryPath, ["checkout", "--quiet", "--detach", headSha]);
  const workPath = join(directory, "work");
  await mkdir(workPath);
  return { repositoryPath, headSha, workPath };
}

async function preview(t, { title, description = "", releaseTags = ["v1.11.0"], commitHead, ...overrides }) {
  const { repositoryPath, headSha, workPath } = await makePullRequest(t, { commitHead });
  const github = makeFakeGitHub({
    pullRequest: { title, description, headSha, baseBranch: "main", ...overrides.pullRequest },
    releaseTags,
  });
  return previewPullRequest({
    github,
    pullRequestNumber: 7,
    checkedOutSha: overrides.checkedOutSha ?? headSha,
    repositoryPath,
    repositoryUrl: REPOSITORY_URL,
    workPath,
    log: NULL_LOG,
    clock: makeFakeClock(),
  });
}

describe("previewPullRequest", () => {
  test("previews a release that bumps the minor for a feature", async (t) => {
    const result = await preview(t, { title: "feat: Add a skill" });

    assert.equal(result.releasedVersion, "1.11.0");
    assert.equal(result.pluginVersion, "1.11.0");
    assert.equal(result.expectedPluginVersion, "1.12.0");
    assert.equal(result.nextRelease.type, "minor");
    assert.equal(result.nextRelease.version, "1.12.0");
    assert.equal(result.nextRelease.name, "sdlc-1.12.0");
  });

  test("renders the release's body with GitHub's links and the installation commands", async (t) => {
    const result = await preview(t, { title: "feat: Add a skill" });

    assert.match(
      result.nextRelease.body,
      /^## \[1\.12\.0\]\(https:\/\/github\.com\/gnarea\/sdlc\/compare\/v1\.11\.0\.\.\.v1\.12\.0\) \(\d{4}-\d{2}-\d{2}\)\n/,
    );
    assert.match(
      result.nextRelease.body,
      /\n### Features\n\n\* Add a skill \(\[#7\]\(https:\/\/github\.com\/gnarea\/sdlc\/issues\/7\)\) \(\[[0-9a-f]{7}\]\(https:\/\/github\.com\/gnarea\/sdlc\/commit\/[0-9a-f]{40}\)\)\n/,
    );
    assert.ok(
      result.nextRelease.body.endsWith(
        "\n## Installing\n\n```text\n/plugin marketplace add gnarea/clone\n/plugin install sdlc@gnarea\n```\n",
      ),
    );
    assert.doesNotMatch(result.nextRelease.body, /unconventional/);
  });

  test("bumps the patch for a fix", async (t) => {
    const result = await preview(t, { title: "fix: Correct a skill" });

    assert.equal(result.expectedPluginVersion, "1.11.1");
  });

  test("bumps the major for a breaking change in the title", async (t) => {
    const result = await preview(t, { title: "feat!: Rename a skill" });

    assert.equal(result.expectedPluginVersion, "2.0.0");
  });

  test("bumps the major for a breaking change in the description", async (t) => {
    const result = await preview(t, {
      title: "feat: Rename a skill",
      description: "Some context.\r\n\r\nBREAKING CHANGE: Callers must use the new name.",
    });

    assert.equal(result.expectedPluginVersion, "2.0.0");
    assert.match(result.nextRelease.body, /### ⚠ BREAKING CHANGES\n\n\* Callers must use the new name\./);
  });

  test("keeps the released version for a change that doesn't release", async (t) => {
    const result = await preview(t, { title: "chore: Bump cspell" });

    assert.equal(result.nextRelease, null);
    assert.equal(result.expectedPluginVersion, "1.11.0");
  });

  test("accepts a change to agents or skills that releases", async (t) => {
    const result = await preview(t, {
      title: "fix: Reword a skill",
      commitHead: (path) => commitFile(path, { path: "skills/programming/SKILL.md", content: "Reworded\n", message: "Reword" }),
    });

    assert.equal(result.expectedPluginVersion, "1.11.1");
  });

  test("accepts a change elsewhere that doesn't release", async (t) => {
    const result = await preview(t, {
      title: "docs: Reword the README",
      commitHead: (path) => commitFile(path, { path: "README.md", content: "Reworded\n", message: "Reword" }),
    });

    assert.equal(result.nextRelease, null);
  });

  for (const path of ["agents/programmer.md", "skills/programming/SKILL.md"]) {
    test(`refuses a change to ${path} that doesn't release`, async (t) => {
      await assert.rejects(
        preview(t, {
          title: "refactor: Reword",
          commitHead: (repositoryPath) => commitFile(repositoryPath, { path, content: "Reworded\n", message: "Reword" }),
        }),
        { message: `Pull request changes agents or skills (${path}), so its type must release a version (got "refactor: Reword")` },
      );
    });
  }

  test("reads the version that squashing the pull request would leave", async (t) => {
    const result = await preview(t, {
      title: "feat: Add a skill",
      commitHead: (path) => commitPluginVersion(path, "1.12.0", "Bump"),
    });

    assert.equal(result.pluginVersion, "1.12.0");
    assert.equal(result.expectedPluginVersion, "1.12.0");
  });

  test("refuses a pull request whose title doesn't follow Conventional Commits", async (t) => {
    await assert.rejects(preview(t, { title: "Add a skill" }), { message: /^Pull request's title must be/ });
  });

  test("refuses a pull request with a line that's too long", async (t) => {
    await assert.rejects(preview(t, { title: "feat: Add a skill", description: "a".repeat(4_001) }), {
      message: /^Each line of the pull request's title and description must have at most 4000 characters/,
    });
  });

  test("refuses a pull request against another branch", async (t) => {
    await assert.rejects(preview(t, { title: "feat: Add a skill", pullRequest: { baseBranch: "next" } }), {
      message: "Pull request's base must be main (got next)",
    });
  });

  test("refuses a pull request whose head isn't the commit checked out", async (t) => {
    const otherSha = "0123456789abcdef0123456789abcdef01234567";

    await assert.rejects(preview(t, { title: "feat: Add a skill", checkedOutSha: otherSha }), {
      message: new RegExp(`^Pull request's head must be the commit checked out \\(got [0-9a-f]{40}, expected ${otherSha}\\)`),
    });
  });

  test("refuses a pull request that conflicts with main", async (t) => {
    const { repositoryPath, headSha, workPath } = await makePullRequest(t, {
      commitHead: (path) => commitPluginVersion(path, "1.12.0", "Bump"),
    });
    await runGit(repositoryPath, ["checkout", "--quiet", "main"]);
    await commitPluginVersion(repositoryPath, "1.11.1", "fix: Correct a skill (#8)");
    await runGit(repositoryPath, ["tag", "v1.11.1"]);
    await runGit(repositoryPath, ["push", "--quiet", "--tags", "origin", "main"]);
    await runGit(repositoryPath, ["fetch", "--quiet", "origin"]);
    await runGit(repositoryPath, ["checkout", "--quiet", "--detach", headSha]);

    await assert.rejects(
      previewPullRequest({
        github: makeFakeGitHub({
          pullRequest: { title: "feat: Add a skill", description: "", headSha, baseBranch: "main" },
          releaseTags: ["v1.11.0", "v1.11.1"],
        }),
        pullRequestNumber: 7,
        checkedOutSha: headSha,
        repositoryPath,
        repositoryUrl: REPOSITORY_URL,
        workPath,
        log: NULL_LOG,
        clock: makeFakeClock(),
      }),
      { message: "Head must merge into the base without conflicts (got conflicts with origin/main)" },
    );
  });

  test("refuses to preview whilst main's version has no release", async (t) => {
    await assert.rejects(preview(t, { title: "feat: Add a skill", releaseTags: [] }), {
      message: "Release v1.11.0 must exist within 5 minutes: re-run the release on main, or publish it by hand",
    });
  });

  test("refuses to preview when main's version was tagged off main", async (t) => {
    const { repositoryPath, headSha, workPath } = await makePullRequest(t);
    await runGit(repositoryPath, ["checkout", "--quiet", "main"]);
    await commitPluginVersion(repositoryPath, "1.12.0", "feat: Add a skill (#8)");
    await runGit(repositoryPath, ["push", "--quiet", "origin", "main"]);
    await runGit(repositoryPath, ["tag", "v1.12.0", headSha]);
    await runGit(repositoryPath, ["push", "--quiet", "origin", "v1.12.0"]);
    await runGit(repositoryPath, ["fetch", "--quiet", "origin"]);
    await runGit(repositoryPath, ["checkout", "--quiet", "--detach", headSha]);

    await assert.rejects(
      previewPullRequest({
        github: makeFakeGitHub({
          pullRequest: { title: "feat: Add a skill", description: "", headSha, baseBranch: "main" },
          releaseTags: ["v1.11.0", "v1.12.0"],
        }),
        pullRequestNumber: 7,
        checkedOutSha: headSha,
        repositoryPath,
        repositoryUrl: REPOSITORY_URL,
        workPath,
        log: NULL_LOG,
        clock: makeFakeClock(),
      }),
      { message: "Release v1.12.0 must be on main (got a tag that isn't)" },
    );
  });
});

describe("formatSummary", () => {
  test("states the version the plugin must have, and the release", () => {
    const summary = formatSummary({
      releasedVersion: "1.11.0",
      nextRelease: { type: "minor", version: "1.12.0", name: "sdlc-1.12.0", body: "## 1.12.0\n\nThe notes.\n" },
    });

    assert.equal(
      summary,
      "# Release preview\n\nSquashing this pull request would make a minor release, so `.claude-plugin/plugin.json` must have version 1.12.0.\n\nThe release would be titled `sdlc-1.12.0`, with these notes:\n\n## 1.12.0\n\nThe notes.\n",
    );
  });

  test("states the version the plugin must keep when nothing releases", () => {
    const summary = formatSummary({ releasedVersion: "1.11.0", nextRelease: null });

    assert.equal(
      summary,
      "# Release preview\n\nSquashing this pull request wouldn't release a new version, so `.claude-plugin/plugin.json` must keep version 1.11.0.\n",
    );
  });
});
