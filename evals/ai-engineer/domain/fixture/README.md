# Tern

Tern is a command-line tool that converts map tiles between formats. We release it every few weeks: a maintainer tags a commit on `main` as `vX.Y.Z`, then publishes a GitHub release whose notes they write by hand from the commits since the previous tag. Each commit's message follows Conventional Commits (e.g., `fix(png): keep the alpha channel`).

Our agents run on a small harness of our own. Each agent is defined in a Markdown file under `agents/`, and the harness offers it the tools that its definition lists, from those in `src/tern_agents/tools.py`.
