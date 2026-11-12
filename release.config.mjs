import { readFile } from "node:fs/promises";
import { join } from "node:path";

const RELEASE_BODY_TEMPLATE = `<%= nextRelease.notes %>
## Installing

\`\`\`text
/plugin marketplace add gnarea/clone
/plugin install sdlc@gnarea
\`\`\`
`;

export default {
  branches: ["main"],
  preset: "conventionalcommits",
  plugins: [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    {
      // CI sets the version in the pull request, so a mismatch means that it was merged before CI could.
      async verifyRelease(_pluginConfig, { cwd, nextRelease }) {
        const manifest = JSON.parse(await readFile(join(cwd, ".claude-plugin/plugin.json"), "utf8"));
        if (manifest.version !== nextRelease.version) {
          throw new Error(`Plugin's version must be ${nextRelease.version} (got ${manifest.version})`);
        }
      },
    },
    [
      "@semantic-release/github",
      {
        releaseBodyTemplate: RELEASE_BODY_TEMPLATE,
        // The release job can't write to issues or pull requests.
        successCommentCondition: false,
        failCommentCondition: false,
      },
    ],
  ],
};
