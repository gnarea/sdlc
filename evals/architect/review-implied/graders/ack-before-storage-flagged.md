---
type: llm
---

The answer says that the design shouldn't be built as it stands, because the receiver responds `200` to Stripe before the event is stored in the database, so an event can be lost for good (e.g., if the insert keeps failing, or the task stops before making it) without Stripe ever resending it.
