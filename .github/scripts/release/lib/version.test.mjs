import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { compareVersions, isVersion } from "./version.mjs";

describe("isVersion", () => {
  for (const value of ["0.0.0", "1.11.0", "10.200.3000"]) {
    test(`accepts ${JSON.stringify(value)}`, () => {
      assert.equal(isVersion(value), true);
    });
  }

  for (const value of ["1.11", "1.11.0.0", "v1.11.0", "01.11.0", "1.11.0-beta.1", "1.11.0+build", "", undefined, 1]) {
    test(`refuses ${JSON.stringify(value)}`, () => {
      assert.equal(isVersion(value), false);
    });
  }
});

describe("compareVersions", () => {
  const cases = [
    { version1: "1.11.0", version2: "1.11.0", sign: 0 },
    { version1: "1.11.0", version2: "1.11.1", sign: -1 },
    { version1: "1.11.0", version2: "1.12.0", sign: -1 },
    { version1: "1.11.0", version2: "2.0.0", sign: -1 },
    { version1: "1.10.0", version2: "1.9.0", sign: 1 },
    { version1: "2.0.0", version2: "1.99.99", sign: 1 },
  ];

  for (const { version1, version2, sign } of cases) {
    test(`compares ${version1} with ${version2}`, () => {
      assert.equal(Math.sign(compareVersions(version1, version2)), sign);
    });
  }

  test("refuses anything other than a version", () => {
    assert.throws(() => compareVersions("1.11.0", "v1.12.0"), {
      message: 'Version must be "(major).(minor).(patch)" (got "v1.12.0")',
    });
  });
});
