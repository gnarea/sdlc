import { COMMIT_TYPES } from "../../../../release.config.mjs";

const CONVENTIONAL_TITLE_PATTERN = new RegExp(`^(?:${COMMIT_TYPES.join("|")})(?:\\([a-z0-9-]+\\))?!?: \\S`);

// The commit parser takes time quadratic in a line's length: a line of 4,000 characters takes under a second, so
// the 17 that fit in a description of 65,536 characters (GitHub's maximum) take a fraction of the job's timeout.
const MAX_LINE_LENGTH = 4_000;

/** Require a pull request's title to follow Conventional Commits, since it becomes the squash commit's title. */
export function requireConventionalTitle(title) {
  if (!CONVENTIONAL_TITLE_PATTERN.test(title)) {
    throw new Error(
      `Pull request's title must be "(type)[(scope)][!]: (description)", with a type among ${COMMIT_TYPES.join(", ")} (got ${JSON.stringify(title)})`,
    );
  }
}

/** Require each line of a squash commit's message to be short enough for the commit parser to finish quickly. */
export function requireShortLines(message) {
  const longestLineLength = Math.max(...message.split("\n").map((line) => line.length));
  if (MAX_LINE_LENGTH < longestLineLength) {
    throw new Error(
      `Each line of the pull request's title and description must have at most ${MAX_LINE_LENGTH} characters (got ${longestLineLength})`,
    );
  }
}

/** Make the message of the commit that GitHub produces when it squashes a pull request. */
export function makeSquashCommitMessage({ number, title, description }) {
  const subject = `${title} (#${number})`;
  const body = description.replaceAll("\r\n", "\n").trim();
  return body === "" ? subject : `${subject}\n\n${body}`;
}
