const CONVENTIONAL_COMMITS_PRESET = "conventionalcommits";

// The only types that the pull request check accepts.
export const COMMIT_TYPES = ["build", "chore", "ci", "docs", "feat", "fix", "perf", "refactor", "revert", "style", "test"];

const RELEASE_BODY_TEMPLATE = `<%= nextRelease.notes %>
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
        releaseBodyTemplate: RELEASE_BODY_TEMPLATE,
        // The release job can't write to issues or pull requests.
        successCommentCondition: false,
        failCommentCondition: false,
      },
    ],
  ],
};
