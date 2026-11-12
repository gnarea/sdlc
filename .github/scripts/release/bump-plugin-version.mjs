import { readEnvironmentVariable } from "./lib/environment.mjs";
import { pushVersionBump } from "./lib/version-bump.mjs";

await pushVersionBump({
  repositoryPath: process.cwd(),
  branch: readEnvironmentVariable("BRANCH"),
  headSha: readEnvironmentVariable("HEAD_SHA"),
  version: readEnvironmentVariable("VERSION"),
});
