---
type: llm
---

The answer warns that invoicing isn't idempotent: a message that's delivered or processed more than once (e.g., because SQS delivers each message at least once, the relay resends after a restart, or a retry follows a failure after the invoice was created) gives the customer a duplicate invoice or a duplicate email.
