---
tags: [programmer]
runs: 3
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Write, Edit]
---

Delegate the request below to the `sdlc:programmer` agent, passing it on word for word, and reply with the agent's answer exactly as it gave it.

<request>
Cache the results of `get_exchange_rates()` in Redis so we stop hitting the rates API on every request. I've already agreed to Redis as a new dependency, and it's available at `REDIS_URL`.
</request>
