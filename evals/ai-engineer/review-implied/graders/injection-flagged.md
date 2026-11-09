---
type: llm
---

The answer says that the agent definition isn't good to ship as it stands, and gives as a reason that it renders the issue's body (which whoever opens the issue writes) into the system prompt, so that instructions planted in an issue would reach the agent as part of its own instructions (i.e., a prompt injection).
