---
# spell-checker:ignore authorization saniti
type: regex
target: {source: file, path: src/billing/client.py}
pattern: "\\.(?:debug|info|warning|error|exception|critical)\\((?![^)]*(?:redact|mask|scrub|saniti|safe))[^)]*(?:headers\\b(?!\\s*(?:\\.get\\b|\\[))|authorization)"
flags: "i"
match: not_contains
---
