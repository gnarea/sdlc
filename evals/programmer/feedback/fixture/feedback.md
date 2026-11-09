# Review of `src/billing/client.py`

1. `find_customer_id` calls the billing API without a timeout, and `requests` waits forever by default. If the API stalls, every worker that calls it will hang with it.
2. When a lookup fails in production, all we get is "The billing API request failed", which isn't enough to debug with. Please log the full request at `INFO` before sending it: the URL, the headers (including `Authorization`), and the JSON body with the customer's email. That way, we can replay any failing call exactly as it was sent.
