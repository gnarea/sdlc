# Support router

Tally is a bookkeeping app for small businesses. When a customer emails its support address, the router moves the email to one of three queues:

- Billing: invoices, payments, refunds, and changes to a customer's plan, which the accounts team handles.
- Technical: bugs, error messages, data imports, and connections to banks, which the support engineers handle.
- Other: everything else, which the support lead sorts by hand.

For each new email, the router makes one request to the model. The system prompt is `prompts/sort-email.md`, and the user prompt is the email's subject and body, in an `<email>` tag. The model answers by calling the `route` tool, whose only parameter, `queue`, must be `billing`, `technical`, or `other`.

Customers write in English, French, or Spanish.
