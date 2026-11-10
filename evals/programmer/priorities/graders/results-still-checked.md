---
type: llm
focus: {source: file, path: src/docs/search.py}
---

`search` still returns only documents that the user may view. It either still calls `can_view` on each result, or filters every result by the user's permissions in another way, such as a single call to `Permissions` that covers all the results, or a query that only selects documents that the user owns or whose space the user belongs to. The file offers no way to skip that check, such as a flag or a separate search that returns unchecked results.
