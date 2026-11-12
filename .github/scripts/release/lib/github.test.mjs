import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { makeGitHubClient, waitForRelease } from "./github.mjs";

const HEAD_SHA = "0123456789abcdef0123456789abcdef01234567";

const PULL_REQUEST = {
  number: 7,
  title: "feat: Add a skill",
  body: "Closes #1.",
  head: { sha: HEAD_SHA },
  base: { ref: "main" },
};

/** Fake of the GitHub API that serves the responses given for each path, and records the requests it gets. */
function makeFakeFetch(responsesByPath) {
  const requests = [];
  async function fetch(url, options) {
    requests.push({ url, options });
    const path = new URL(url).pathname;
    const response = responsesByPath[path] ?? { status: 404, body: "{}" };
    if (response instanceof Error) {
      throw response;
    }
    return new Response(response.body, { status: response.status });
  }
  return { fetch, requests };
}

function makeClient(responsesByPath) {
  const { fetch, requests } = makeFakeFetch(responsesByPath);
  return { github: makeGitHubClient({ repository: "gnarea/sdlc", token: "the-token", fetch }), requests };
}

describe("readPullRequest", () => {
  test("returns the pull request", async () => {
    const { github } = makeClient({
      "/repos/gnarea/sdlc/pulls/7": { status: 200, body: JSON.stringify(PULL_REQUEST) },
    });

    assert.deepEqual(await github.readPullRequest(7), {
      number: 7,
      title: "feat: Add a skill",
      description: "Closes #1.",
      headSha: HEAD_SHA,
      baseBranch: "main",
    });
  });

  test("authenticates with the token, with a timeout", async () => {
    const { github, requests } = makeClient({
      "/repos/gnarea/sdlc/pulls/7": { status: 200, body: JSON.stringify(PULL_REQUEST) },
    });

    await github.readPullRequest(7);

    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, "https://api.github.com/repos/gnarea/sdlc/pulls/7");
    assert.equal(requests[0].options.headers.Authorization, "Bearer the-token");
    assert.ok(requests[0].options.signal instanceof AbortSignal);
  });

  test("returns an empty description when there's none", async () => {
    const { github } = makeClient({
      "/repos/gnarea/sdlc/pulls/7": { status: 200, body: JSON.stringify({ ...PULL_REQUEST, body: null }) },
    });

    assert.equal((await github.readPullRequest(7)).description, "");
  });

  test("refuses an unsuccessful response", async () => {
    const { github } = makeClient({ "/repos/gnarea/sdlc/pulls/7": { status: 404, body: "{}" } });

    await assert.rejects(github.readPullRequest(7), { message: "GitHub must return pull request #7 (got HTTP 404)" });
  });

  test("refuses a response over the maximum length", async () => {
    const { github } = makeClient({
      "/repos/gnarea/sdlc/pulls/7": { status: 200, body: " ".repeat(1_000_001) },
    });

    await assert.rejects(github.readPullRequest(7), {
      message: "GitHub's response must have at most 1000000 characters (got 1000001)",
    });
  });

  const malformedPullRequests = [
    { name: "a missing number", pullRequest: { ...PULL_REQUEST, number: "7" }, message: /^Pull request must have/ },
    { name: "a missing title", pullRequest: { ...PULL_REQUEST, title: null }, message: /^Pull request must have/ },
    { name: "a description that isn't a string", pullRequest: { ...PULL_REQUEST, body: 1 }, message: /^Pull request must have/ },
    {
      name: "a malformed head commit",
      pullRequest: { ...PULL_REQUEST, head: { sha: "main" } },
      message: "Pull request #7 must have a head commit",
    },
    {
      name: "a missing base branch",
      pullRequest: { ...PULL_REQUEST, base: null },
      message: "Pull request #7 must have a base branch",
    },
  ];

  for (const { name, pullRequest, message } of malformedPullRequests) {
    test(`refuses a pull request with ${name}`, async () => {
      const { github } = makeClient({
        "/repos/gnarea/sdlc/pulls/7": { status: 200, body: JSON.stringify(pullRequest) },
      });

      await assert.rejects(github.readPullRequest(7), { message });
    });
  }
});

describe("hasRelease", () => {
  test("says a release exists when GitHub returns it", async () => {
    const { github } = makeClient({ "/repos/gnarea/sdlc/releases/tags/v1.11.0": { status: 200, body: "{}" } });

    assert.equal(await github.hasRelease("v1.11.0"), true);
  });

  test("says a release doesn't exist when GitHub can't find it", async () => {
    const { github } = makeClient({});

    assert.equal(await github.hasRelease("v1.11.0"), false);
  });

  test("refuses any other response", async () => {
    const { github } = makeClient({ "/repos/gnarea/sdlc/releases/tags/v1.11.0": { status: 502, body: "" } });

    await assert.rejects(github.hasRelease("v1.11.0"), {
      message: "GitHub must say whether release v1.11.0 exists (got HTTP 502)",
    });
  });
});

describe("waitForRelease", () => {
  /** Fake of GitHub that publishes the release after a number of checks, or fails the checks given. */
  function makeFakeGitHub({ checksBeforeRelease = Infinity, failingChecks = [] } = {}) {
    const checkedTags = [];
    return {
      checkedTags,
      async hasRelease(tag) {
        checkedTags.push(tag);
        if (failingChecks.includes(checkedTags.length)) {
          throw new Error("GitHub is down");
        }
        return checksBeforeRelease < checkedTags.length;
      },
    };
  }

  /** Fake clock whose sleeps advance its time, and are recorded. */
  function makeFakeClock() {
    let time = 0;
    const sleeps = [];
    return {
      sleeps,
      now: () => time,
      async sleep(milliseconds) {
        sleeps.push(milliseconds);
        time += milliseconds;
      },
    };
  }

  test("returns straight away when the release exists", async () => {
    const github = makeFakeGitHub({ checksBeforeRelease: 0 });
    const clock = makeFakeClock();

    await waitForRelease(github, "v1.11.0", clock);

    assert.deepEqual(github.checkedTags, ["v1.11.0"]);
    assert.deepEqual(clock.sleeps, []);
  });

  test("polls with exponential backoff until the release exists", async () => {
    const github = makeFakeGitHub({ checksBeforeRelease: 4 });
    const clock = makeFakeClock();

    await waitForRelease(github, "v1.11.0", clock);

    assert.equal(github.checkedTags.length, 5);
    assert.deepEqual(clock.sleeps, [5_000, 10_000, 20_000, 40_000]);
  });

  test("retries a failed check", async () => {
    const github = makeFakeGitHub({ checksBeforeRelease: 1, failingChecks: [1] });
    const clock = makeFakeClock();

    await waitForRelease(github, "v1.11.0", clock);

    assert.equal(github.checkedTags.length, 2);
  });

  test("gives up before the deadline of 5 minutes", async () => {
    const github = makeFakeGitHub();
    const clock = makeFakeClock();

    await assert.rejects(waitForRelease(github, "v1.11.0", clock), {
      message: "Release v1.11.0 must exist within 5 minutes: re-run the release on main, or publish it by hand",
    });
    assert.deepEqual(clock.sleeps, [5_000, 10_000, 20_000, 40_000, 60_000, 60_000, 60_000]);
    assert.ok(clock.now() <= 5 * 60_000);
  });

  test("chains the last error when it gives up", async () => {
    const github = makeFakeGitHub({ failingChecks: [8] });
    const clock = makeFakeClock();

    await assert.rejects(waitForRelease(github, "v1.11.0", clock), (error) => {
      assert.equal(error.cause.message, "GitHub is down");
      return true;
    });
  });
});
