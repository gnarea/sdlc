import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { makeSquashCommitMessage, requireConventionalTitle, requireShortLines } from "./pull-request.mjs";

describe("requireConventionalTitle", () => {
  const validTitles = [
    "feat: Add a skill",
    "fix: Correct the `programming` skill",
    "docs: Explain the evals",
    "refactor: Split the `systems-architecture` skill",
    "test: Add an eval",
    "ci: Release automatically",
    "chore: Bump cspell from 10.4.0 to 10.5.0",
    "revert: Add a skill",
    "feat(programmer): Add a principle",
    "feat(systems-architecture): Add a principle",
    "feat!: Rename a skill",
    "feat(programmer)!: Remove a skill",
  ];

  for (const title of validTitles) {
    test(`accepts ${JSON.stringify(title)}`, () => {
      requireConventionalTitle(title);
    });
  }

  const invalidTitles = [
    "Add a skill",
    "feature: Add a skill",
    "perf: Speed up the evals",
    "Feat: Add a skill",
    "feat:Add a skill",
    "feat: ",
    "feat(): Add a skill",
    "feat(Programmer): Add a skill",
    "feat!(programmer): Add a skill",
    " feat: Add a skill",
    'Revert "feat: Add a skill"',
  ];

  for (const title of invalidTitles) {
    test(`refuses ${JSON.stringify(title)}`, () => {
      assert.throws(() => requireConventionalTitle(title), {
        message: `Pull request's title must be "(type)[(scope)][!]: (description)", with a type among feat, fix, docs, refactor, test, ci, chore, revert (got ${JSON.stringify(title)})`,
      });
    });
  }
});

describe("requireShortLines", () => {
  test("accepts lines of up to 4,000 characters", () => {
    requireShortLines(`feat: Add a skill\n\n${"a".repeat(4_000)}\n${"b".repeat(4_000)}`);
  });

  test("refuses a line of more than 4,000 characters", () => {
    assert.throws(() => requireShortLines(`feat: Add a skill\n\n${"a".repeat(4_001)}`), {
      message: "Each line of the pull request's title and description must have at most 4000 characters (got 4001)",
    });
  });
});

describe("makeSquashCommitMessage", () => {
  test("appends the number to the title, as GitHub does", () => {
    assert.equal(
      makeSquashCommitMessage({ number: 7, title: "feat: Add a skill", description: "" }),
      "feat: Add a skill (#7)",
    );
  });

  test("separates the description from the title with a blank line", () => {
    assert.equal(
      makeSquashCommitMessage({ number: 7, title: "feat: Add a skill", description: "Closes #1.\n\nMore." }),
      "feat: Add a skill (#7)\n\nCloses #1.\n\nMore.",
    );
  });

  test("uses Unix line endings and trims the description", () => {
    assert.equal(
      makeSquashCommitMessage({ number: 7, title: "feat: Add a skill", description: "\r\nCloses #1.\r\n\r\nMore.\r\n" }),
      "feat: Add a skill (#7)\n\nCloses #1.\n\nMore.",
    );
  });

  test("leaves out a description of whitespace", () => {
    assert.equal(
      makeSquashCommitMessage({ number: 7, title: "feat: Add a skill", description: "\r\n " }),
      "feat: Add a skill (#7)",
    );
  });
});
