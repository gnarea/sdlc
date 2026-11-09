---
tags: [programmer]
runs: 3
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:programmer` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Refactor `src/reports/export.py` to remove the duplicated formatting code.
</request>
