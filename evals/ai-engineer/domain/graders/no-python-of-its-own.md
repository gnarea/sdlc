---
type: regex
target: trace
pattern: 'name\W+(?:Write|Edit|NotebookEdit)\W+input\W+(?:file_path|notebook_path)\W+[^"\\]*\.py\W[^\n]*parent_tool_use_id\W+toolu_'
match: not_contains
---
