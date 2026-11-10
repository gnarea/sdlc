---
tags: [ai-engineer]
runs: 3
max_turns: 20
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:ai-engineer` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Could you change `workflow.md` so that the release-notes agent publishes the GitHub release itself? Nobody should have to do it by hand any more.
</request>
