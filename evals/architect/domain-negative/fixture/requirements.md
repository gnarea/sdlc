# Storing suppliers' invoices

Suppliers send us their invoices as PDFs, which our accounts payable team uploads to Payables, the internal tool in which we approve and pay them. Payables keeps each PDF in a `bytea` column of its PostgreSQL database, which has grown to 600 GB, so its backups and restores now take hours.

We need to decide where the PDFs should live instead, and how long we keep them.

## What we know

- We get about 4,000 invoices a month, of 300 KB each on average, and 20 MB at most.
- The team views each invoice in the browser whilst approving it, usually within a week of its upload. Our auditors ask for older invoices a few times a year.
- Finance says that HMRC requires us to keep each invoice for 6 years from the end of the financial year it relates to. Our financial year ends on 31 March.
- Invoices hold suppliers' bank details, and sometimes the name and home address of a sole trader.
- Only the accounts payable team and our auditors may see them.
- Payables runs on Amazon ECS in our AWS account, in the `eu-west-2` region, next to its Amazon RDS for PostgreSQL database. Other systems of ours already keep their exports in Amazon S3.
