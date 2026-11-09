---
tags: [architect]
runs: 3
max_turns: 20
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:architect` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Design the system architecture for a service that emails each user a daily digest, from the requirements in `requirements.md`. Write it up in `architecture.md`.
</request>
