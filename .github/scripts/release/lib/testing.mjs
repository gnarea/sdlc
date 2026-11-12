import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

import { runGit } from "./git.mjs";
import { PLUGIN_MANIFEST_PATH } from "./plugin-manifest.mjs";

export async function makeTemporaryDirectory(t) {
  const path = await mkdtemp(join(tmpdir(), "release-test-"));
  t.after(() => rm(path, { recursive: true, force: true }));
  return path;
}

/** Make a repository with a remote called `origin`, as a workflow's checkout has. */
export async function makeRepositoryWithOrigin(t) {
  const directory = await makeTemporaryDirectory(t);
  const originPath = join(directory, "origin.git");
  const repositoryPath = join(directory, "repository");
  await runGit(directory, ["init", "--quiet", "--bare", "--initial-branch=main", originPath]);
  await runGit(directory, ["clone", "--quiet", originPath, repositoryPath]);
  await runGit(repositoryPath, ["symbolic-ref", "HEAD", "refs/heads/main"]);
  await runGit(repositoryPath, ["config", "commit.gpgSign", "false"]);
  await runGit(repositoryPath, ["config", "tag.gpgSign", "false"]);
  return { directory, originPath, repositoryPath };
}

export async function commitFile(repositoryPath, { path, content, message }) {
  const absolutePath = join(repositoryPath, path);
  await mkdir(dirname(absolutePath), { recursive: true });
  await writeFile(absolutePath, content, "utf8");
  await runGit(repositoryPath, ["add", "--", path]);
  await runGit(repositoryPath, ["commit", "--quiet", "--message", message]);
  return runGit(repositoryPath, ["rev-parse", "HEAD"]);
}

export async function commitPluginVersion(repositoryPath, version, message) {
  return commitFile(repositoryPath, {
    path: PLUGIN_MANIFEST_PATH,
    content: `${JSON.stringify({ name: "sdlc", version }, null, 2)}\n`,
    message,
  });
}

export async function commitEmpty(repositoryPath, message) {
  await runGit(repositoryPath, ["commit", "--quiet", "--allow-empty", "--message", message]);
  return runGit(repositoryPath, ["rev-parse", "HEAD"]);
}
