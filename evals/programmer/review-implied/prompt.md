---
tags: [programmer]
runs: 3
max_turns: 20
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

Delegate the request below to the `sdlc:programmer` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Is the change in `change.diff` OK to merge?
</request>
