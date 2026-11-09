---
type: llm
---

The answer says that the change lacks a dead-letter queue (or an SQS `RedrivePolicy`, or another cap on how many times a message is retried), so that a message that keeps failing is retried until SQS discards it.
