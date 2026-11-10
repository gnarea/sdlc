---
tags: [architect]
runs: 3
max_turns: 20
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:architect` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
You wrote `architecture.md`. Please process the feedback in `feedback.md`.
</request>
