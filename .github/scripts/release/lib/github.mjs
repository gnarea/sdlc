import { setTimeout as sleepFor } from "node:timers/promises";

const API_URL = "https://api.github.com";

const REQUEST_TIMEOUT_MILLISECONDS = 10_000;

// A pull request's description is at most 65,536 characters, and the rest of the response is a few kilobytes.
const MAX_RESPONSE_LENGTH = 1_000_000;

const COMMIT_SHA_PATTERN = /^[0-9a-f]{40}$/;

// A release on `main` usually takes about a minute, but the run may wait for a runner first.
const RELEASE_WAIT_MILLISECONDS = 5 * 60_000;
const FIRST_POLL_DELAY_MILLISECONDS = 5_000;
const MAX_POLL_DELAY_MILLISECONDS = 60_000;

/**
 * Make a client for the GitHub API that reads what a pull request's checks need from a repository.
 *
 * `fetch` is the I/O boundary, so tests can replace it.
 */
export function makeGitHubClient({ repository, token, fetch = globalThis.fetch }) {
  async function get(path) {
    const response = await fetch(`${API_URL}/repos/${repository}${path}`, {
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "X-GitHub-Api-Version": "2022-11-28",
      },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MILLISECONDS),
    });
    const body = await response.text();
    if (MAX_RESPONSE_LENGTH < body.length) {
      throw new Error(`GitHub's response must have at most ${MAX_RESPONSE_LENGTH} characters (got ${body.length})`);
    }
    return { status: response.status, body };
  }

  return {
    async readPullRequest(number) {
      const { status, body } = await get(`/pulls/${number}`);
      if (status !== 200) {
        throw new Error(`GitHub must return pull request #${number} (got HTTP ${status})`);
      }
      return decodePullRequest(JSON.parse(body));
    },

    async hasRelease(tag) {
      const { status } = await get(`/releases/tags/${encodeURIComponent(tag)}`);
      if (status === 404) {
        return false;
      }
      if (status !== 200) {
        throw new Error(`GitHub must say whether release ${tag} exists (got HTTP ${status})`);
      }
      return true;
    },
  };
}

/**
 * Wait until a release exists, polling with exponential backoff until the deadline.
 *
 * Errors are retried until then, since the request is safe to repeat.
 */
export async function waitForRelease(github, tag, { now = Date.now, sleep = sleepFor } = {}) {
  const deadline = now() + RELEASE_WAIT_MILLISECONDS;
  let delay = FIRST_POLL_DELAY_MILLISECONDS;
  let lastError;
  while (true) {
    try {
      if (await github.hasRelease(tag)) {
        return;
      }
      lastError = undefined;
    } catch (error) {
      lastError = error;
    }

    if (deadline <= now() + delay) {
      throw new Error(
        `Release ${tag} must exist within ${RELEASE_WAIT_MILLISECONDS / 60_000} minutes: re-run the release on main, or publish it by hand`,
        { cause: lastError },
      );
    }
    await sleep(delay);
    delay = Math.min(delay * 2, MAX_POLL_DELAY_MILLISECONDS);
  }
}

function decodePullRequest(pullRequest) {
  const { number, title, body, head, base } = pullRequest;
  if (!Number.isInteger(number) || typeof title !== "string" || (body !== null && typeof body !== "string")) {
    throw new Error("Pull request must have a number, a title, and a description or none");
  }
  if (!COMMIT_SHA_PATTERN.test(head?.sha)) {
    throw new Error(`Pull request #${number} must have a head commit`);
  }
  if (typeof base?.ref !== "string") {
    throw new Error(`Pull request #${number} must have a base branch`);
  }
  return {
    number,
    title,
    description: body ?? "",
    headSha: head.sha,
    baseBranch: base.ref,
  };
}
