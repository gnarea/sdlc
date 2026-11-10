# Help desk labeller

Each email that reaches the help desk gets two labels, so that it lands with the right team: the product that it's about, and whether the customer asks for a refund. The help desk receives about 6,000 emails on a weekday.

For each new email, the worker makes one request to the model, with the body of `agents/classifier.md` as the system prompt, and the email in an `<email>` tag as the user prompt. The model answers by calling the `label` tool, whose schema only allows the values that the system prompt lists.

The worker reads the model's full ID and the effort level from the front matter's `model` and `effort`, and refuses to start without them.
