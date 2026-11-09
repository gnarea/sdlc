# Order-ahead prototype plan

We want to let customers order and pay on their phones before they reach one of our 14 bakeries, and collect their order without queuing. The prototype puts the ordering journey in front of regular customers, and establishes whether orders can reach the shops' tills in time to be ready when the customer walks in.

## Questions

### Would regulars order ahead for their morning visit?

- **Risk**: Two thirds of our sales happen between 7:00 and 9:00, when the queues are longest. If regulars wouldn't change their habits, order-ahead isn't worth its cost, and we'd add a second till in the busiest shops instead.
- **Approach**: Put a clickable mock-up of the ordering journey in front of 20 regulars in the Mill Road and Station Street shops, who've agreed to take part in exchange for a free coffee. Ask each one to place their usual order for the next morning, and record how many complete it without help. Then ask whether they'd use it at least once a week, and what would stop them.

### Can orders reach the shop's till within 30 seconds?

- **Risk**: Staff start preparing an order when it appears on the till. If orders take longer to arrive than a customer takes to walk in from the car park, the order won't be ready, and we'd need a screen in each kitchen instead, which is a separate project with its own budget.
- **Approach**: Hypothesis: the till vendor's order API delivers an order to the shop's till within 30 seconds of submission. Test: build a mock of the order API from the vendor's documentation, with the response times that the documentation states, and submit 200 orders to it, one every 15 seconds. Refuted if any order takes longer than 30 seconds to arrive, or if any order is lost.

### Would regulars rather pay with Apple Pay or Google Pay?

- **Risk**: None that we know of. The payment provider enables both at no extra cost, so the app will offer both either way.
- **Approach**: Build two versions of the mock-up's payment screen, one with each wallet as the default, and show each version to half of the regulars. Count how many keep the default, and how many switch.

## Non-goals

- Delivery: we'll only consider it once order-ahead has proven itself.
- Loyalty points: the existing loyalty card stays as it is.

## Compromises

- **Fixed menu**: The mock-up shows a fixed menu, rather than each shop's stock for the day, since the stock system already feeds the website's menus without issues.
