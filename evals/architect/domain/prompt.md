---
tags: [architect]
runs: 3
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

Delegate the request below to the `sdlc:architect` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Design how the mobile app syncs notes with the server, and list the files and functions in our codebase that need to change for it. The requirements are in `requirements.md`.
</request>
