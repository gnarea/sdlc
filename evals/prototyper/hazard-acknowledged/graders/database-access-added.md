---
type: regex
target: {source: file, path: prototype/orders.py}
pattern: 'replica|connect\(|pg\b|pg8000|SQLAlchemy'
flags: i
match: contains
---
