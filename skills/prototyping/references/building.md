# Building a prototype

- Effort MUST go into what the questions depend on. Whatever is already known to work MUST be left out or stubbed.
- Whatever only serves software that has to last SHOULD be left out, whether in the code (e.g., unit tests, documentation, continuous integration, linting, the conventions of the codebase it's built in) or in the system (e.g., retries, dead-lettering, degraded operation, scaling, alerting, backups, the versioning of contracts, infrastructure as code). Telemetry SHOULD cover only what the questions measure.
- In an existing codebase, the prototype MUST be kept apart from the code that ships (e.g., on a temporary Git branch), so that none of it can ship by accident.
- A path outside the main journeys MAY be left unimplemented. Where one is, it MUST fail immediately and state that the case is unsupported, so that the gap can't be mistaken for a defect.
