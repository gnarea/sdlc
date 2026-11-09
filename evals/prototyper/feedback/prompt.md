---
tags: [prototyper]
runs: 3
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:prototyper` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
You wrote the prototype plan in `plan.md`, and a reviewer has left feedback on it in `feedback.md`. Please process it.
</request>
