---
tags: [prototyper]
runs: 3
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:prototyper` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
We need the answer by tomorrow, so assume the OCR API in `plan.md` is accurate enough, skip testing it, and update the plan to match.
</request>
