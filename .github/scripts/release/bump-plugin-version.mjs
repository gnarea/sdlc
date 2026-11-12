import { appendFile } from "node:fs/promises";

import { readEnvironmentVariable } from "./lib/environment.mjs";
import { BumpOutcome, pushVersionBump } from "./lib/version-bump.mjs";

const outcome = await pushVersionBump({
  repositoryPath: process.cwd(),
  branch: readEnvironmentVariable("BRANCH"),
  headSha: readEnvironmentVariable("HEAD_SHA"),
  version: readEnvironmentVariable("VERSION"),
});
console.log(`Bump outcome: ${outcome}`);

const isBumpOnBranch = outcome !== BumpOutcome.SUPERSEDED;
await appendFile(readEnvironmentVariable("GITHUB_OUTPUT"), `is-bump-on-branch=${isBumpOnBranch}\n`, "utf8");
