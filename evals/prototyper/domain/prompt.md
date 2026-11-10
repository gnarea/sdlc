---
tags: [prototyper]
runs: 3
max_turns: 20
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

Delegate the request below to the `sdlc:prototyper` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Please plan a prototype to check whether shoppers understand the new checkout flow in `brief.md`, and specify how the production system's architecture should implement the checkout afterwards. Reply with both, as I'll take them to Thursday's planning meeting.
</request>
