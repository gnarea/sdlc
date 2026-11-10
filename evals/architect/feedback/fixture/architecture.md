# Bookkeeping app

The bookkeeping app is a web app in which small businesses keep their books: their invoices, their expenses, and the reconciliation of their bank statements. Each business has a _workspace_, whose members sign in with an email address and a password.

## Purpose

Small businesses need books that are accurate, that nobody but them and their accountant can see, and that show who changed what.

Non-goals:

- Payroll.
- Filing tax returns.

### Users and other stakeholders

- **Workspace members**: Keep the books from a browser. They need nobody outside their workspace to see their books, and to get back into their account quickly if they forget their password.
- **Workspace owners**: Need to see who changed what in their workspace over the past 12 months, which is how long our terms promise to keep that history.
- **Support staff**: Help members who are locked out. They can't see a workspace's books unless its owner grants them access.

## Principles

### Nobody outside a workspace can read its books

This includes support staff and operators, unless the owner grants them access, which the audit log records. It protects members' financial data at the expense of slower support.

## Components

- **Web app**: A container on Amazon ECS, behind an Application Load Balancer. It's the only component that members and support staff interact with.
- **Accounts database**: An Amazon RDS for PostgreSQL database holding each member's email address and password hash.
  - Passwords are hashed with Argon2id. A member who forgets their password resets it through a link that we email them, which expires after 30 minutes. Support staff can send that email, but can't set or see a password.
  - A closed account is deleted 30 days after it's closed.
- **Books database**: A separate RDS for PostgreSQL database holding each workspace's books. A workspace's books are deleted 30 days after it's closed.
- **Audit log**: An append-only table in the books database, with an entry for each change to a workspace's books: who made it, when, from which IP address, and what changed.
  - Only the web app's audit role can insert entries, and nothing can update or delete them.
  - Owners read their workspace's entries in the web app.
- **Sessions**: Kept in the accounts database, and expire after 14 days.

Both databases have automated backups, with 35 days of point-in-time recovery.
