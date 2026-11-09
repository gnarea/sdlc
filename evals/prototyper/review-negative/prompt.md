---
tags: [prototyper]
runs: 3
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:prototyper` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Plan a prototype to find out whether our Raspberry Pi gateway can decode 50 video streams at once, and write the plan in `prototype-plan.md`. The gateway's details are in the README. We have to decide by the end of the month whether to order Pis for the new sites, or move to bigger hardware.
</request>
