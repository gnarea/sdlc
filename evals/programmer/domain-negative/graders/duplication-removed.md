---
type: regex
target: {source: file, path: src/reports/export.py}
pattern: "%\\s*100\\b[\\s\\S]*%\\s*100\\b"
match: not_contains
---
