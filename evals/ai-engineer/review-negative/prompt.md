---
tags: [ai-engineer]
runs: 3
max_turns: 20
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:ai-engineer` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Write the system prompt for an agent that sorts incoming support emails into billing, technical, or other. Please save it as `prompts/sort-email.md`; how the router uses it is in `README.md`.
</request>
