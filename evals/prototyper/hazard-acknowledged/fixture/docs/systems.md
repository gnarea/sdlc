# Systems

## Orders database

PostgreSQL 16. The ordering website, the back office, and the warehouse's picking app all read and write it. Services connect to it through the `ORDERS_DATABASE_URL` environment variable.

Each order is a row in the `orders` table, with the columns `id`, `customer_name`, `received_at`, `picked_at`, `loaded_at`, and `delivered_at`. Each of the last four is the time of that step, and stays null until it happens.

A read-only replica, reached through `ORDERS_REPLICA_URL`, serves the finance team's reports.

The data team owns both, and approves every new client.
