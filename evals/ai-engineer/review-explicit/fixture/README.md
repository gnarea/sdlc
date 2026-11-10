# Design digest

Every Monday, the digest job summarises each design document that changed in the wiki during the past week, and posts the summaries to the engineering channel, so that engineers can tell which changes concern them without reading every document.

For each document, the job sends one request to `claude-haiku-5-5` at `medium` effort. Its system prompt is `prompts/system.md`, and its user prompt is `prompts/summarise.md`, rendered with Jinja2 for that document. The job posts the model's reply to the channel as it is.
