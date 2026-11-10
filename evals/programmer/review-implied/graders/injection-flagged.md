---
type: llm
---

The answer says that the change mustn't be merged as it stands, because `find_users_by_name` puts `name` into the SQL query by string formatting, which allows SQL injection.
