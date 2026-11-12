import assert from "node:assert/strict";
import { afterEach, describe, test } from "node:test";

import { readEnvironmentVariable, readPullRequestNumber } from "./environment.mjs";

const VARIABLE_NAME = "RELEASE_TEST_VARIABLE";

afterEach(() => {
  delete process.env[VARIABLE_NAME];
});

describe("readEnvironmentVariable", () => {
  test("returns the variable's value", () => {
    process.env[VARIABLE_NAME] = "value";

    assert.equal(readEnvironmentVariable(VARIABLE_NAME), "value");
  });

  for (const [name, value] of [["unset", undefined], ["empty", ""]]) {
    test(`refuses an ${name} variable`, () => {
      if (value !== undefined) {
        process.env[VARIABLE_NAME] = value;
      }

      assert.throws(() => readEnvironmentVariable(VARIABLE_NAME), {
        message: `Environment variable ${VARIABLE_NAME} must be set`,
      });
    });
  }
});

describe("readPullRequestNumber", () => {
  test("returns the number", () => {
    process.env[VARIABLE_NAME] = "70";

    assert.equal(readPullRequestNumber(VARIABLE_NAME), 70);
  });

  for (const value of ["0", "07", "-1", "1.5", "7 ", "seven"]) {
    test(`refuses ${JSON.stringify(value)}`, () => {
      process.env[VARIABLE_NAME] = value;

      assert.throws(() => readPullRequestNumber(VARIABLE_NAME), {
        message: `Environment variable ${VARIABLE_NAME} must be a pull request's number (got ${JSON.stringify(value)})`,
      });
    });
  }
});
