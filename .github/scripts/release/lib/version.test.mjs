import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { isVersion } from "./version.mjs";

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
