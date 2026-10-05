# Documenting a system's architecture

An architecture is documented so that another architect, who could be a person, can assess it. What the design costs other stakeholders (e.g., a residual risk, a limitation with no workaround) MUST be called out in the documents below.

## The architecture document

**The architecture document is the system's _constitution_**: the considerations, desiderata, and trade-offs that its design answers to, written up front to guide every later decision and change. A system designed from scratch MUST have one before it's built, and any other system SHOULD have one. Every change MUST comply with it. It SHOULD rarely be amended, and each amendment MUST be justified on its own merits, never by the change that prompted it. When writing one, the architecture document template SHOULD be used as a guide, not as a strict template.

The document MUST cover:

- The problem, stated separately from the design, so that either can be falsified without the other.
- The groups of users (e.g., staff, external users), followed by the other stakeholders (e.g., operators).
- The non-goals, and the deferred decisions.
- The principles that every change must comply with, in order of priority, each with what it optimises for and at the expense of what.
- The leading alternative for each group of users and, where it serves a group better, what the system offers them instead.
- The most constrained environment the system must run in, and the users or other stakeholders that each constraint comes from (e.g., external users on a five-year-old Android version, operators who must deploy on-premises).
- The components, which groups of users interact with each, what each knows about the people it serves (including what a broker can observe about the traffic it relays), and whom each trusts with what.
- Every party that stakeholders must trust, and with what. Where anonymity or deniability is a requirement, what each operator could be compelled to disclose, alter, or block, and the size of any crowd that anonymity depends on.
- Each backing service, named by the capability it provides (e.g., "an S3-compatible object store") rather than by product, wherever someone else could deploy the system. Where the system is coupled to one provider, it MUST say so, along with the layers that are deliberately not portable.
- The limit, caveat, or dependency that each delegation (to a provider, the platform, or third-party software) imposes.
- Each legal or contractual obligation that the design relies on, and what happens if it's breached.
- Each existing standard that could serve part of the design, whether it's adopted, and why.
- A reference to the threat model.
- Known limitations, including where there's no workaround.
- Each ethical cost that the design can't discharge.

## The threat model

The threat model is a living document of its own: a change MUST update whatever it makes stale in it. When writing one, the threat model template SHOULD be used as a guide, not as a strict template.

It MUST cover the adversaries and their capabilities, including any capability that the design pre-empts and how far ahead that bet is. Each attack vector MUST state its impact, attempt likelihood, method, mitigations, and residual risks, and vectors SHOULD be ordered by likelihood. It MUST also say who bears each residual risk, and which mitigations fall to whoever deploys the system.

## The change spec

A change spec specifies a delta to the system's architecture: what the change adds, alters, or removes. The starting point is the architecture as it stands, which is nothing in a new system. It MUST use the medium that suits the change (e.g., an issue, an RFC). When writing one, the change spec template SHOULD be used as a guide, not as a strict template. When reviewing one, it MUST be judged on whether it provides what's needed to assess the change, whatever its structure.

- The spec MUST cover every element that the change adds or alters in enough detail to be built and reviewed without guesswork: everything about an element it adds, and only what changes about one it alters. For example:
  - For each exchange: whether it's asynchronous, synchronous, or a stream (and, if synchronous, why it can't be asynchronous), the protocol, the message schema, authentication, size limits, timeouts, the retry policy (backoff, jitter, and whether it's capped by attempts or by time), and what happens once retries are exhausted.
  - For each endpoint that accepts traffic: rate limits, quotas, and other protections against abuse.
  - For each store: the schema, indices, uniqueness constraints, retention and what enforces it, who can read it, and whether it's backed up.
  - For each component: its identity and permissions, and how it's deployed and scaled.
  - For each failure mode: whose fault it is, the response, and the severity.
  - For each dependency: how the system behaves when it's unavailable.
  - For each configuration option: its default.
- A message format SHOULD be declared in the notation closest to its wire format (e.g., Protocol Buffers for gRPC, JSON for a JSON API, ASN.1 for DER), marking what the change adds, alters, or removes.
- Decisions nest, and each MUST state what it optimises for, at the expense of what, and its second-order consequences.
- Open questions MUST sit next to the decision they block.
- A rejected option MUST be documented with its reasoning, rather than deleted.
- Where the change drops a requirement or reverses a decision, the spec MUST:
  1. Restate the current design in its own best terms.
  2. Say what was wrong with the original requirement, on its own terms.
  3. Enumerate every simplification that the reversal buys.
  4. Enumerate the capabilities it costs and the consequences being accepted, and say why the advantages still outweigh them.

## Diagrams

Any of these documents SHOULD use a diagram wherever it conveys at a glance what prose would take longer to say (e.g., an overview of the system early in the document, a sequence diagram of a protocol's exchanges). A diagram MAY replace prose. Where more prescription is needed than a diagram can carry and stay simple, prose SHOULD complement it, and MUST NOT repeat what it already shows.
