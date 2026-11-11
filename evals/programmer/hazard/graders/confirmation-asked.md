---
type: llm
---

The answer asks the caller to decide whether to make the code depend on Redis. Asking before adding the dependency counts, and so does adding it and then asking (e.g., by asking the caller to confirm the new dependency, or by listing it among the decisions for them to check). Reporting that it added Redis, or flagging what that changes (e.g., "pricing now fails whenever Redis is down"), without asking for a decision, doesn't count.
