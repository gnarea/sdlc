---
type: regex
target: {source: file, path: pyproject.toml}
pattern: "redis"
flags: "i"
match: not_contains
---
