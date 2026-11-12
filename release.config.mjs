const CONVENTIONAL_COMMITS_PRESET = "conventionalcommits";

// The pull request check only accepts these types, which CLAUDE.md defines for the plugin.
export const COMMIT_TYPES = ["feat", "fix", "docs", "refactor", "test", "ci", "chore", "revert"];

export const RELEASE_NAME_TEMPLATE = "sdlc-<%= nextRelease.version %>";

export const RELEASE_BODY_TEMPLATE = `<%= nextRelease.notes %>
## Installing

\`\`\`text
/plugin marketplace add gnarea/clone
/plugin install sdlc@gnarea
\`\`\`
`;

export const COMMIT_ANALYZER_PLUGIN = ["@semantic-release/commit-analyzer", { preset: CONVENTIONAL_COMMITS_PRESET }];

export const RELEASE_NOTES_GENERATOR_PLUGIN = [
  "@semantic-release/release-notes-generator",
  { preset: CONVENTIONAL_COMMITS_PRESET },
];

export default {
  branches: ["main"],
  plugins: [
    COMMIT_ANALYZER_PLUGIN,
    RELEASE_NOTES_GENERATOR_PLUGIN,
    "./.github/scripts/release/verify-plugin-version.mjs",
    [
      "@semantic-release/github",
      {
        releaseNameTemplate: RELEASE_NAME_TEMPLATE,
        releaseBodyTemplate: RELEASE_BODY_TEMPLATE,
        // The release job can't write to issues or pull requests.
        successCommentCondition: false,
        failCommentCondition: false,
      },
    ],
  ],
};
