# Order-tracking prototype plan

Account managers spend about a third of their day on calls from restaurants asking where their order is. The prototype puts a tracking page in front of them, to learn whether it would answer those calls faster than the back office does today, where they piece the answer together from three screens.

## Questions

### Would the tracking page let account managers answer calls faster?

- **Risk**: The project's case rests on saving account managers' time. If the page doesn't answer calls faster, we'll improve the back office's search instead.
- **Approach**: Put the tracking page in front of six account managers, in one-hour sessions, and ask each one to answer ten typical questions from restaurants about the orders on the page. Time each answer, and compare it with today's median of four minutes per call, from the phone system's logs.

### Which details do account managers need on the page?

- **Risk**: Each detail comes from a different system (the warehouse's picking app, the vans' trackers, or the drivers' delivery app), and each one takes weeks to integrate. We'll only integrate the ones that account managers use.
- **Approach**: In the same sessions, note which of the page's details (picking status, van, estimated arrival, and proof of delivery) each account manager uses to answer each question.

## Compromises

- **Sample orders**: The page shows made-up orders from `prototype/sample_orders.json`, rather than orders from the orders database, since the questions are about what account managers do with the page.
- **No login**: The page runs only on the facilitator's laptop, on `localhost`, during the sessions, so only the account manager taking part can see it.
