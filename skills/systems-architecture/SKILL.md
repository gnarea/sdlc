---
name: systems-architecture
description: How to design systems beyond the boundary of the OS process. Scope, decomposition, data, messaging, failure, backing services, security and privacy, impact on others, operability, and integration testing. Use when designing, changing, or reviewing a system's architecture or its infrastructure code.
---
# Systems architecture

## Problem and scope

- The problem MUST be analysed independently of any solution to it (e.g., by surveying known approaches and their weaknesses) before a design is chosen.
- Before a mechanism is designed for a requirement, the requirement MUST be challenged: dropping one can remove a cascade of mechanisms (e.g., dropping peer authentication can remove a handshake, and a bespoke protocol). Every capability that the drop costs MUST be weighed against every simplification it buys.
- Where time or resources fall short, the problem MUST be narrowed (e.g., fewer use cases, platforms, features), and the standard to which the rest is built MUST NOT be lowered.
- Non-goals MUST be decided before the design, and a mechanism that only serves a non-goal MUST NOT be built.
- Where an established standard does the job (e.g., a protocol, a data format, a cryptographic scheme), it SHOULD be adopted in place of a bespoke mechanism. It SHOULD be declined only where it lacks a production-ready implementation in a language or on a platform that the system must support.
- The design MUST be compared against the leading alternative for each group of users it targets. Where the alternative serves a group better, the design MUST close the gap, or concede that group and decide what it offers them instead.
- The design MUST work in the most constrained environment it must support (e.g., hardware, connectivity, power, budget, a platform that can't be upgraded), and treat anything better as an optimisation.
- Where a problem can't be solved by technical means alone, or a technical solution would be much simpler alongside a legal or contractual obligation (e.g., a no-logs clause in the Terms of Service), the design SHOULD rely on such an obligation, and MUST limit the damage should it be breached.
- Only what is expensive to reverse (e.g., identifiers, wire formats, schemas) MUST be decided up front. The rest SHOULD wait for evidence.

## Decomposition

- Components MUST be delineated by coupling and cohesion first, and then given the least data, authority, and reach that their job requires.
- Two parts of the system MUST be separate components where different organisations operate them, or where they must start, stop, or scale independently (e.g., video transcoding that needs many more servers than the website that takes the uploads). They MUST also be separate where one must not hold data or authority that the other has. Otherwise, they SHOULD be one component.
- A component that some deployments don't need MUST be independently deployable.

## Data

- Data the system doesn't need MUST be designed out, rather than collected and protected by a promise not to look at it. This includes data about people who aren't users (e.g., the contacts in an uploaded address book).
- Every piece of data that is stored MUST have a purpose, a set of readers, and a retention period, and the store SHOULD enforce the retention period (e.g., with a TTL index).
- Personal data MUST NOT be replicated to a system with weaker retention, access control, or jurisdiction than its source.
- Personal data MUST NOT be shared with a party that doesn't need it, especially where it would let that party correlate a person across contexts.
- Identifiers exposed to third parties MUST NOT be guessable, and MUST NOT leak the time or the volume of what they identify (e.g., a UUIDv4, rather than a sequential or timestamp-derived database ID).
- A store that holds original data MUST be backed up. A store whose data can be rebuilt reliably and cheaply from original data (e.g., a search index) needn't be, unless a backup serves a purpose that rebuilding can't.
- Idempotency SHOULD come from natural keys and a uniqueness constraint. Where the work has no natural key (e.g., a payment), or is too costly to repeat, a record of what was already done (e.g., the identifiers of the messages processed) MAY be kept instead.

## Messaging

- Asynchronous messaging MUST be the default, because a message that is durably stored can be retried, redelivered, or dead-lettered after any failure, whereas request-response ties each component's availability to the others'. Request-response MUST be used only where the exchange can't be made asynchronous (e.g., a third-party API that only offers it).
- Every exchange MUST tolerate the other party being unreachable.
- Whatever is acknowledged (e.g., a message, an item in a stream) MUST be acknowledged only once it's safe for the sender to forget: durably stored and flushed (e.g., with `fdatasync`), or fully processed, rather than merely received or parsed.
- Every message, whether exchanged synchronously or asynchronously, MUST carry the version of its format from its first release, because a version can't be retrofitted once messages are in use. The version MAY travel as metadata rather than in the payload (e.g., in the media type, such as `application/vnd.example.order.v1+json`).
- Work that many parties start at once (e.g., on a schedule, in response to the same event) MUST be spread with random jitter, so that they don't act in lockstep.

## Failure

- The design MUST decide how the system behaves when each dependency is unavailable, and degraded operation MUST be a modelled state, not an error.
- Each failure mode MUST be attributed to the sender, the system, or the infrastructure, and the attribution MUST determine the response, the severity, and whether to retry. Severity MUST be set by who has to act, and how soon.
- Every retry policy MUST be capped, by attempts or by elapsed time, and MUST space attempts with exponential backoff and jitter. Where the message being sent expires, retries MUST also stop once it has.
- A failure that a later attempt can't overcome (e.g., malformed input) MUST NOT be retried.
- Where an operation updates more than one store, the platform MUST make the update atomic, or the operation MUST be safe to repeat after failing partway.

## Backing services and providers

- The system MUST run as little as it can: managed services SHOULD be preferred, and compute SHOULD cost nothing whilst idle unless a requirement rules that out.
- Every delegation (to a provider, the platform, or third-party software) MUST be weighed against the limit, caveat, or dependency it imposes.
- Where others would deploy the system themselves, each backing service MUST be chosen by the capability it provides (e.g., an S3-compatible object store), rather than by product.
- Where only we deploy the system, it SHOULD be coupled to a single provider.
- An abstraction whose upkeep outweighs the portability it buys (e.g., a pluggable database) MUST be refused.

## Security and privacy

### Trust

- Traffic that a component relays without needing to read MUST be encrypted end-to-end past it, and the metadata it observes MUST be minimised.
- The parties that stakeholders must trust, and what they must trust them with, MUST be minimised. Where trust can't be designed out, how the trusted party operates the system MUST be open to outside scrutiny (e.g., by publishing the infrastructure code).
- Every host that the system contacts MUST be enumerated in its documentation, with the reason.
- Unsafe use of an API, a wire format, or a deployment's configuration MUST be impossible: no skipping a check, turning off a security property, or downgrading. Where a choice is unavoidable, offer a few named options, all of them safe.

### Anonymity

Where anonymity or deniability is a requirement:

- A single component MUST NOT hold enough to defeat it (e.g., both an address and the traffic sent to it).
- Operators SHOULD hold nothing that they could be compelled to disclose, alter, or block.
- Where anonymity depends on a crowd, the design MUST favour deployments that keep it large (e.g., a shared gateway over a self-hosted one).

### Threat model

- Every system MUST be designed against a threat model naming its adversaries and their capabilities, including those that are feasible today but not yet in use.
- The threat model MUST include the system's own users and operators as adversaries of other users (e.g., a stalker abusing location sharing).
- Where others would deploy the system themselves, the threat model MUST cover the adversaries that their deployments would face, and the design MUST say which mitigations fall to the operator.
- A mitigation MUST NOT be assumed complete: for each, the design MUST identify what would defeat it, what that would cost the attacker (where it can be estimated), and whether those who bear that residual risk can accept it.

## Impact beyond the system

- The system MUST NOT be able to overwhelm another system, whether ours or anyone else's, through abuse, a bug, or a misconfiguration, including at the scale the design targets. Every outbound flow MUST be capped per destination, and an input MUST NOT be able to trigger more outbound work than its sender could have done directly (e.g., through a webhook, a link preview, a fan-out that turns one request into many).
- The system MUST NOT send more to a source address than it received from it until the address is verified, so that it can't be used to amplify an attack on a third party.
- The system's environmental cost MUST be factored in: where providers or regions are otherwise comparable, the one powered by cleaner energy SHOULD be chosen, and work that can be deferred (e.g., batch jobs) SHOULD run where and when energy is cleanest.
- Resources the system consumes on devices it doesn't own (e.g., mobile data, battery, storage) are a cost to their owners, and MUST NOT be spent on work that doesn't serve them unless they consent to it (e.g., relaying other users' traffic).
- Users MUST be able to leave with their data, in a documented format that another implementation could import.
- What runs on a user's device MUST keep doing whatever doesn't inherently need our servers when they're unreachable, including after the service shuts down.

## Operability

- An operator MUST be able to tell what the system is doing, how well, and whose fault a failure is, without a developer. Every behaviour observable from outside MUST be logged. Metrics and traces SHOULD cover it too, except where they don't apply or aren't desirable.
- Where the platform asks a process to stop (e.g., SIGTERM), it MUST stop accepting work and exit within the grace period it's given.
- Whatever collects, stores, or alerts on telemetry (e.g., a log aggregator, a paging service) MUST be deemed a backing service.
- The design MUST decide how telemetry leaves each process (e.g., written to standard output for the platform to collect, pushed to a collector), so that no component depends on where it ends up.
- Every operation that the threat model expects to be abused MUST be measured in the product's own terms (e.g., accounts created per hour), with an alert on departures from the norm.
- Where privacy is a requirement, observability MUST be derived from the threat model: record what's needed to detect and troubleshoot abuse, and nothing that could identify a user.
- Configuration options SHOULD be kept to a minimum, and each default MUST be safe for every deployment.

## Integration testing

- Tests SHOULD use a real instance of every backing service, run locally or provisioned per test run, and each run MUST get its own isolated instance or namespace. Where no such instance can be run (e.g., a proprietary service without an emulator), a test double MAY be used instead.
- Where operators choose the backend of a backing service at deployment time, every supported backend MUST be tested on every change, so that none can rot unnoticed.
- Where tests use a substitute for a provider that real deployments use (e.g., an emulator, a compatible alternative), that provider MUST also be exercised on a schedule (e.g., weekly), to catch drift and breaking changes without the cost and risk of using it on every change.
- The deployed system SHOULD be testable end-to-end, through a supported artefact where third parties integrate with it.
- Tests MUST cover the most constrained environment that the design supports.

## Additional guidelines

### By artefact

- [Server-side systems](references/server-side-systems.md): Part of the system runs on servers that we or another operator run.
- [End-user systems](references/end-user-systems.md): Part of the system is installed on a device the user controls.

### By concern

- Inter-process communication:
  - [Asynchronous messaging](references/asynchronous-messaging.md): The design involves a broker, a queue, or any other exchange where the sender doesn't wait for the outcome.
  - [Synchronous messaging](references/synchronous-messaging.md): The design involves request-response, whether as the client or the server.
  - [Streams](references/streams.md): The design involves a long-lived connection that carries a series of items (e.g., a WebSocket, a gRPC stream).
  - [Contracts between systems](references/contracts.md): The change defines or alters a contract that another system, team, or organisation depends on.
- [Telemetry](references/telemetry.md): The design affects a diagnostic signal that the system emits.
- [Denial of service and abuse](references/abuse.md): An entry point is reachable by untrusted parties.
- [Cloud infrastructure](references/cloud-infrastructure.md): The change provisions or alters infrastructure at a cloud provider.
- [Documenting a system's architecture](references/documentation.md): The design, or a change to it, is being documented or specified.
- [Prototyping](references/prototyping.md): The artefact is a prototype built to answer a design question.

### Templates

- [Architecture document](assets/architecture.md)
- [Threat model](assets/threat-model.md)
- [Change spec](assets/change-spec.md)
