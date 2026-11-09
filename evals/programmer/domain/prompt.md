---
tags: [programmer]
runs: 3
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:programmer` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Add a `summarise_ticket(ticket)` function to `src/support/summaries.py` that calls our LLM client in `src/support/llm.py`, and write the system prompt that the model should use for it.
</request>
