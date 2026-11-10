# Feedback on the bookkeeping app's architecture

1. **The audit log has no retention period.** Every other store says how long it keeps its data, but the audit log doesn't, so it would keep members' IP addresses forever. Our terms only promise owners 12 months of history.
2. **Support can't tell members their password.** Members who forget their password keep asking support for it, and many give up on the reset email before it arrives. Instead of hashing passwords, store them with reversible encryption (e.g., AES-256-GCM, with a KMS key that the support console can use), so that support can read a member's password back to them once they've confirmed who they are.
