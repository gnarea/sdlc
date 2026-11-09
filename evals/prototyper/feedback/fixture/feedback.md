# Feedback on the appointment-reminders prototype plan

1. **The appointments question can't fail.** Its approach says what we'll fetch, but not which result would refute the hypothesis, so fetching any appointments at all would count as a pass. I'd add something like "Refuted if any of the test appointments is missing from what the API returns, or has the wrong date or time."
2. **Drop the question about whether practice managers would pay.** It's the hardest one to test: we'd need 12 busy practice managers' time, and a letter of intent doesn't bind them to anything anyway. We can answer the two technical questions within the team in a week, so I'd focus the prototype on those.
