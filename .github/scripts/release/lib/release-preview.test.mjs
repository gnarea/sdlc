import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { Writable } from "node:stream";
import { describe, test } from "node:test";

import { runGit } from "./git.mjs";
import { PreviewOutcome, formatSummary, previewPullRequest } from "./release-preview.mjs";
import { commitEmpty, commitFile, commitPluginVersion, makeRepositoryWithOrigin } from "./testing.mjs";

const REPOSITORY_URL = "https://github.com/gnarea/sdlc.git";

const NULL_LOG = new Writable({ write: (_chunk, _encoding, callback) => callback() });

/** Fake of GitHub that serves one pull request. */
function makeFakeGitHub(pullRequest) {
  const readNumbers = [];
  return {
    readNumbers,
    async readPullRequest(number) {
      readNumbers.push(number);
      return { number, ...pullRequest };
    },
  };
}

/**
 * Make a repository whose `main` released 1.11.0, then got a commit that doesn't release, plus a pull request's head
 * with the commit given, checked out as the job has it.
 *
 * `changeMain` can then change `main` before the job fetches it.
 */
async function makePullRequest(t, { commitHead, changeMain = async () => {} }) {
  const { directory, repositoryPath } = await makeRepositoryWithOrigin(t);
  await commitPluginVersion(repositoryPath, "1.11.0", "Release sdlc 1.11.0 (#62)");
  await runGit(repositoryPath, ["tag", "v1.11.0"]);
  await commitEmpty(repositoryPath, "Add an unconventional change (#70)");
  await runGit(repositoryPath, ["push", "--quiet", "--tags", "origin", "main"]);
  await runGit(repositoryPath, ["checkout", "--quiet", "-b", "feature"]);
  const headSha = await commitHead(repositoryPath);
  await runGit(repositoryPath, ["checkout", "--quiet", "main"]);
  await changeMain(repositoryPath);
  await runGit(repositoryPath, ["push", "--quiet", "--tags", "origin", "main"]);
  await runGit(repositoryPath, ["fetch", "--quiet", "origin"]);
  await runGit(repositoryPath, ["checkout", "--quiet", "--detach", headSha]);
  const workPath = join(directory, "work");
  await mkdir(workPath);
  return { repositoryPath, headSha, workPath };
}

async function preview(
  t,
  { title, description = "", commitHead = (path) => commitEmpty(path, "Change"), changeMain, pullRequest = {} },
) {
  const { repositoryPath, headSha, workPath } = await makePullRequest(t, { commitHead, changeMain });
  return previewPullRequest({
    github: makeFakeGitHub({ title, description, headSha, baseBranch: "main", ...pullRequest }),
    pullRequestNumber: 7,
    checkedOutSha: headSha,
    repositoryPath,
    repositoryUrl: REPOSITORY_URL,
    workPath,
    log: NULL_LOG,
  });
}

describe("previewPullRequest", () => {
  test("previews a release that bumps the minor for a feature", async (t) => {
    const result = await preview(t, { title: "feat: Add a skill" });

    assert.equal(result.outcome, PreviewOutcome.PREVIEWED);
    assert.equal(result.releasedVersion, "1.11.0");
    assert.equal(result.nextRelease.type, "minor");
    assert.equal(result.nextRelease.version, "1.12.0");
    assert.equal(result.nextRelease.name, "v1.12.0");
    assert.equal(result.versionToBump, "1.12.0");
  });

  test("generates the release notes with GitHub's links", async (t) => {
    const result = await preview(t, { title: "feat: Add a skill" });

    assert.match(
      result.nextRelease.notes,
      /^## \[1\.12\.0\]\(https:\/\/github\.com\/gnarea\/sdlc\/compare\/v1\.11\.0\.\.\.v1\.12\.0\) \(\d{4}-\d{2}-\d{2}\)\n/,
    );
    assert.match(
      result.nextRelease.notes,
      /\n### Features\n\n\* Add a skill \(\[#7\]\(https:\/\/github\.com\/gnarea\/sdlc\/issues\/7\)\) \(\[[0-9a-f]{7}\]\(https:\/\/github\.com\/gnarea\/sdlc\/commit\/[0-9a-f]{40}\)\)\n/,
    );
    assert.doesNotMatch(result.nextRelease.notes, /unconventional/);
  });

  test("bumps the patch for a fix", async (t) => {
    const result = await preview(t, { title: "fix: Correct a skill" });

    assert.equal(result.versionToBump, "1.11.1");
  });

  test("bumps the major for a breaking change in the title", async (t) => {
    const result = await preview(t, { title: "feat!: Rename a skill" });

    assert.equal(result.versionToBump, "2.0.0");
  });

  test("bumps the major for a breaking change in the description", async (t) => {
    const result = await preview(t, {
      title: "feat: Rename a skill",
      description: "Some context.\r\n\r\nBREAKING CHANGE: Callers must use the new name.",
    });

    assert.equal(result.versionToBump, "2.0.0");
    assert.match(result.nextRelease.notes, /### ⚠ BREAKING CHANGES\n\n\* Callers must use the new name\./);
  });

  test("keeps the version for a change that doesn't release", async (t) => {
    const result = await preview(t, { title: "chore: Bump cspell" });

    assert.equal(result.nextRelease, null);
    assert.equal(result.versionToBump, null);
  });

  test("bumps nothing when the head already has the version", async (t) => {
    const result = await preview(t, {
      title: "feat: Add a skill",
      commitHead: (path) => commitPluginVersion(path, "1.12.0", "Bump"),
    });

    assert.equal(result.nextRelease.version, "1.12.0");
    assert.equal(result.versionToBump, null);
  });

  test("undoes a bump that no longer releases", async (t) => {
    const result = await preview(t, {
      title: "chore: Bump cspell",
      commitHead: (path) => commitPluginVersion(path, "1.12.0", "Bump"),
    });

    assert.equal(result.versionToBump, "1.11.0");
  });

  test("builds on main's version even if it has no release yet", async (t) => {
    const result = await preview(t, {
      title: "fix: Correct a skill",
      changeMain: (path) => commitPluginVersion(path, "1.12.0", "feat: Add a skill (#8)"),
    });

    assert.equal(result.releasedVersion, "1.12.0");
    assert.equal(result.nextRelease.version, "1.12.1");
    assert.doesNotMatch(result.nextRelease.notes, /Add a skill/);
  });

  test("bumps a version that conflicts with main's", async (t) => {
    const result = await preview(t, {
      title: "fix: Correct a skill",
      commitHead: (path) => commitPluginVersion(path, "1.11.1", "Bump"),
      changeMain: async (path) => {
        await commitPluginVersion(path, "1.12.0", "feat: Add a skill (#8)");
        await runGit(path, ["tag", "v1.12.0"]);
      },
    });

    assert.equal(result.versionToBump, "1.12.1");
  });

  test("previews a pull request that conflicts with main in another file", async (t) => {
    const result = await preview(t, {
      title: "docs: Reword the README",
      commitHead: (path) => commitFile(path, { path: "README.md", content: "Feature\n", message: "Reword" }),
      changeMain: (path) => commitFile(path, { path: "README.md", content: "Main\n", message: "docs: Reword (#8)" }),
    });

    assert.equal(result.outcome, PreviewOutcome.PREVIEWED);
    assert.equal(result.versionToBump, null);
  });

  test("accepts a change to agents or skills that releases", async (t) => {
    const result = await preview(t, {
      title: "fix: Reword a skill",
      commitHead: (path) => commitFile(path, { path: "skills/programming/SKILL.md", content: "Reworded\n", message: "Reword" }),
    });

    assert.equal(result.versionToBump, "1.11.1");
  });

  test("accepts a change elsewhere that doesn't release", async (t) => {
    const result = await preview(t, {
      title: "docs: Reword the README",
      commitHead: (path) => commitFile(path, { path: "README.md", content: "Reworded\n", message: "Reword" }),
    });

    assert.equal(result.nextRelease, null);
  });

  test("ignores changes to agents or skills on main", async (t) => {
    const result = await preview(t, {
      title: "docs: Reword the README",
      commitHead: (path) => commitFile(path, { path: "README.md", content: "Reworded\n", message: "Reword" }),
      changeMain: (path) => commitFile(path, { path: "skills/a/SKILL.md", content: "A\n", message: "Unconventional (#8)" }),
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
        {
          message: `Pull request changes agents or skills (${path}), so its type must release a version, such as feat or fix (got "refactor: Reword")`,
        },
      );
    });
  }

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

  test("leaves a pull request whose head moved on to the run for the new head", async (t) => {
    const result = await preview(t, {
      title: "Not even conventional",
      pullRequest: { headSha: "0123456789abcdef0123456789abcdef01234567" },
    });

    assert.deepEqual(result, { outcome: PreviewOutcome.SUPERSEDED });
  });

  test("reads the pull request with the number given", async (t) => {
    const { repositoryPath, headSha, workPath } = await makePullRequest(t, {
      commitHead: (path) => commitEmpty(path, "Change"),
    });
    const github = makeFakeGitHub({ title: "chore: Bump cspell", description: "", headSha, baseBranch: "main" });

    await previewPullRequest({
      github,
      pullRequestNumber: 7,
      checkedOutSha: headSha,
      repositoryPath,
      repositoryUrl: REPOSITORY_URL,
      workPath,
      log: NULL_LOG,
    });

    assert.deepEqual(github.readNumbers, [7]);
  });
});

describe("formatSummary", () => {
  test("states the release and the version to bump to", () => {
    const summary = formatSummary({
      outcome: PreviewOutcome.PREVIEWED,
      releasedVersion: "1.11.0",
      nextRelease: { type: "minor", version: "1.12.0", name: "v1.12.0", notes: "## 1.12.0\n\nThe notes.\n" },
      versionToBump: "1.12.0",
    });

    assert.equal(
      summary,
      "# Release preview\n\nSquashing this pull request would make a minor release, titled `v1.12.0`.\n\nThe version in `.claude-plugin/plugin.json` has to change to 1.12.0.\n\n## 1.12.0\n\nThe notes.\n",
    );
  });

  test("states the release alone when the version is already right", () => {
    const summary = formatSummary({
      outcome: PreviewOutcome.PREVIEWED,
      releasedVersion: "1.11.0",
      nextRelease: { type: "minor", version: "1.12.0", name: "v1.12.0", notes: "## 1.12.0\n" },
      versionToBump: null,
    });

    assert.equal(summary, "# Release preview\n\nSquashing this pull request would make a minor release, titled `v1.12.0`.\n\n## 1.12.0\n");
  });

  test("states the version the plugin keeps when nothing releases", () => {
    const summary = formatSummary({
      outcome: PreviewOutcome.PREVIEWED,
      releasedVersion: "1.11.0",
      nextRelease: null,
      versionToBump: null,
    });

    assert.equal(
      summary,
      "# Release preview\n\nSquashing this pull request wouldn't release a new version, so the plugin stays at 1.11.0.\n",
    );
  });

  test("says when the head moved on", () => {
    assert.equal(
      formatSummary({ outcome: PreviewOutcome.SUPERSEDED }),
      "# Release preview\n\nThe pull request's head has moved on, so the run for the new head previews it.\n",
    );
  });
});
