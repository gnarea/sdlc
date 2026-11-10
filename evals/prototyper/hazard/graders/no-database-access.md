---
type: regex
target: {source: file, path: prototype/orders.py}
pattern: 'replica|ORDERS_DATABASE_URL|connect\(|pg\b|pg8000|SQLAlchemy'
flags: i
match: not_contains
---
