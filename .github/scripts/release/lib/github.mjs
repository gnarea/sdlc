const API_URL = "https://api.github.com";

const REQUEST_TIMEOUT_MILLISECONDS = 10_000;

// A pull request's description is at most 65,536 characters, and the rest of the response is a few kilobytes.
const MAX_RESPONSE_LENGTH = 1_000_000;

const COMMIT_SHA_PATTERN = /^[0-9a-f]{40}$/;

/**
 * Make a client for the GitHub API that reads a repository's pull requests.
 *
 * `fetch` is the I/O boundary, so tests can replace it.
 */
export function makeGitHubClient({ repository, token, fetch = globalThis.fetch }) {
  return {
    async readPullRequest(number) {
      const response = await fetch(`${API_URL}/repos/${repository}/pulls/${number}`, {
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
      if (response.status !== 200) {
        throw new Error(`GitHub must return pull request #${number} (got HTTP ${response.status})`);
      }
      return decodePullRequest(JSON.parse(body));
    },
  };
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
