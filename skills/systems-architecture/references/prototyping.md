# Prototyping

A prototype exists to answer its questions as quickly as possible, so it gives up whatever only matters to a system that lasts.

## Lifecycle

- The prototype MUST be chartered by the questions it must answer (e.g., what is infeasible, how much capacity it needs), not by a demonstration. Those questions MUST be written down before the design is.
- Where the prototype differs from what production would require, the difference MUST be marked where the cut is made, so that it can't be mistaken for a decision.
- The prototype MUST end with a written conclusion, and every finding that changes the design MUST become tracked work.
- Once its questions are answered, the prototype MUST be archived. It MUST NOT be deployed to production.

## Relaxations

Every rule in the skill applies, except as follows.

- The design MUST cover only what the questions depend on. A component, a backing service, or an exchange that is already known to work MAY be left out, even where production couldn't do without it (e.g., authentication, encryption).
- Whatever a question is about (e.g., a network, a provider, a device) MUST be the real thing, rather than a substitute for it.
- The design MAY be documented in whatever form is quickest: the prototype needs no architecture document, threat model, or change spec of its own.
- Whatever only serves a system that lasts MAY be left out: retries, dead-lettering, degraded operation, scaling, alerting, backups, and the versioning and compatibility of contracts. Telemetry is needed only for what the questions measure.
- Infrastructure MAY be provisioned by hand. It MUST be removed when the prototype is archived, along with any data that it collected.

## Limits

- Nothing above extends to people who aren't taking part: the prototype MUST NOT be able to overwhelm another system or be used against one, and MUST NOT collect their data or spend their devices' resources.
- A protection for those who do take part MAY be left out only where they're told before they use the prototype, and can decline.
