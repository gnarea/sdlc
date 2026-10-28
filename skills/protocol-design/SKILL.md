---
name: protocol-design
description: How to design protocols, including cryptographic ones. Use when designing, changing, or reviewing a protocol, or a protocol specification.
---
# Protocol design

A _protocol_ is the messages that two or more parties exchange, and the rules for exchanging them. This skill extends the `systems-architecture` skill, which applies in full, and only covers what changes when the design subject is a protocol.

## Scope

- The protocol MUST only prescribe the interactions that need its parties to agree.
- Where the protocol leaves out a concern that it could be expected to cover (e.g., a limit on the size of a message, how a party obtains its credentials), the specification MUST say what covers it instead (e.g., the protocol that carries it, the protocols that run on top of it, each implementation).

## Layering

A protocol usually runs on top of another, which carries its messages (aka its _underlying protocol_), and may carry the messages of others in turn (e.g., TCP runs on top of IP, HTTP runs on top of TCP). Every mechanism in the protocol, including authentication and key agreement, MUST work with the delay, loss, duplication, and reordering of the underlying protocol.

Where the protocol has to run over more than one underlying protocol (e.g., HTTP, WebSocket, AMQP):

- A separate protocol (aka a _binding_) MUST carry its messages over each one.
- The protocol MUST state what it requires from every binding (e.g., that messages arrive intact, in order, at the intended party alone), and MUST NOT rely on anything else about any one of them.

Where the protocol leaves anything for other protocols to define (e.g., its bindings, the protocols that run on top of it):

- The protocol MUST list everything that each of them can or has to define (e.g., how each binding acknowledges a message, which identifier each protocol on top uses to tell its messages apart).
- Each of them MUST define whatever that list requires it to, and MUST NOT override anything that the protocol defines.
- A requirement, recommendation, or permission that more than one of them would need MUST be defined by the protocol itself.

## Failures

- Where a failure is the sender's fault (e.g., an invalid message), the recipient SHOULD tell it what was wrong (e.g., in free text alongside a status code).
- Where signalling a failure would reveal something that the sender isn't entitled to know (e.g., whether an account exists), the failure MUST be indistinguishable from an outcome that reveals nothing (e.g., a request that's still pending).
- The protocol, or each of its bindings where it has them, MUST say how implementations treat a failure signal that it doesn't define (e.g., in an HTTP binding, an undocumented `4xx` status code isn't retried, whilst an undocumented `5xx` one is).

## Interoperability

- The protocol MUST allow exactly one way to do each thing (e.g., one way to identify the signer of a message), unless a use case needs another, because every alternative is one more thing that implementations have to agree on to work together. Where it adopts a standard that offers alternatives, it MUST narrow them down likewise.
- Where the protocol does allow alternatives (e.g., versions, algorithms), it MUST name at least one that every implementation has to support (aka _mandatory to implement_), so that any two implementations always have one in common. Where it leaves the alternatives for other protocols to define (e.g., a core protocol that's agnostic of algorithms, like CMS), each of those protocols MUST name one instead.
- Where the protocol extends a standard (e.g., CMS, HTTP), it MUST do so only through the extension points that the standard offers (e.g., a signed attribute, a header field), so that existing implementations of the standard can still process its messages.
- Where no standard fills a gap, the invention MUST be the smallest that fills it, and the specification MUST say which gap that is.
- The protocol MUST NOT require anything (e.g., an algorithm) unless it has a production-ready implementation on every platform that the protocol has to support, and those implementations interoperate with each other.
- A requirement that proves hard to implement with the mainstream tools of a supported platform SHOULD be reconsidered.
- Every constraint that the protocol places on one party MUST also be enforced by the parties that rely on it (e.g., a verifier refusing a credential that's valid for longer than the maximum), so that one lax party can't defeat it.
- Where other protocols run on top of this one, it SHOULD define a trivial one of its own (e.g., one that echoes every message back to its sender), so that implementations and deployments can be tested end-to-end.

## Wire formats

- The messages that the protocol exists to deliver SHOULD be serialised in a binary format (e.g., ASN.1 DER, Protocol Buffers), which is smaller to store and transmit, and quicker to parse.
- Any other exchange between two parties (e.g., a client registering with a server) MAY use whatever format is common in their stack (e.g., Protocol Buffers where the underlying protocol is gRPC), so that neither has to implement another for it.
- The type of a message and the version of its format MUST always travel with it. They SHOULD travel as metadata where the underlying protocol carries it reliably (e.g., a media type in HTTP), and in the payload otherwise.

## Limits

- Every limit MUST be an exact number (e.g., in octets, in seconds). Where it's derived from other limits, the specification MUST show the arithmetic (e.g., the largest payload plus the overhead of the fields around it), and where it's arbitrary, the specification MUST say so.
- Where messages carry an expiry date, the protocol MUST cap how far ahead it can be.
- Where parties exchange timestamps, the tolerance for clock skew SHOULD depend on how well the parties involved can keep time (e.g., hours where one of them can be offline for weeks), rather than be a single figure for the whole protocol.

## Identifiers

- An identifier that implementations only need to compare (e.g., the identifier of a key) MUST be an opaque value: the protocol MUST NOT give it a structure that they'd have to validate (e.g., by requiring it to be a number).
- A party's identifier SHOULD be derived from its key (e.g., a digest of the public key), unless people have to read it.
- Where a party is identified by a name that people read (e.g., a user name), the protocol MUST constrain the name so that one can't easily pass for another (e.g., a PRECIS profile, a ban on the character that separates a name from its domain).

## Versioning and extensibility

- Each format and interface in the protocol MUST have a version of its own, expressed in whatever way is native to it (e.g., an octet at the start of a binary format, a field in a schema, a segment in a URL path, a media type), so that one can change without the others.
- An upgrade MUST NOT require every party to upgrade at once: during the transition, recipients MUST accept the previous version alongside the new one. A message whose type or version a recipient doesn't recognise MUST be refused, and MUST NOT cause any other failure.
- Every identifier that could clash with one that someone else assigns (e.g., a message type, an algorithm identifier) MUST be allocated from a namespace that the protocol's owner controls (e.g., an OID arc, the vendor tree of media types), and MUST NOT be reassigned. Third parties that extend the protocol MUST allocate theirs from a namespace of their own.
- Where a set of values may have to change without a new version of the protocol (e.g., the algorithms that it allows), the set MUST be kept in a registry that's maintained separately from the specification, and in which any value can be deprecated, including one that's mandatory to implement.
- A value MAY be reserved for an addition that's foreseeable but not yet feasible (e.g., a key type that some supported platforms lack), so that it can arrive without a change to the format.

## Intermediaries

- Every party that handles a message, including one that only relays it, MUST validate whatever matters to it before processing or relaying the message.
- Where messages pass through an intermediary (e.g., a broker), the protocol SHOULD let the parties detect a message that it dropped, or keep it from singling one out to drop (e.g., by hiding the type of each message from it).
- An intermediary that isn't trusted MUST NOT be able to replay a message undetected (e.g., a sequence number inside the encrypted message, which the response echoes).
- Where the parties at either end keep a session, it SHOULD outlive the connection that carries it, so that it can resume through another intermediary.

## Privacy

Privacy is always a requirement, but how far the protocol has to take it varies by project.

- The protocol MUST be assessed for what each party that handles or observes a message learns from it besides its content (e.g., when it was created, its size, who initiated the exchange, what the recipient asked for). Each leak MUST be mitigated in the protocol itself (e.g., by backdating a timestamp, padding the message, moving a field inside the encrypted payload), or the specification MUST state what the party learns.
- An identifier or credential that would let an observer link a party's activity across its peers (e.g., the same intermediate certificate in every message) SHOULD be left out of messages.
- Privacy requirements on the protocol's dependencies (e.g., that DNS queries are encrypted) MUST be part of the protocol, rather than left to deployment guidance.
- A countermeasure to traffic analysis MUST be assessed for whether it makes the traffic stand out (e.g., a pattern that changes with every connection, a pattern that every server shares), and against an adversary who controls the component that applies it (e.g., a compromised relay that hands out decoy traffic to see who collects it).

## Additional guidelines

### By concern

- [Cryptography](references/cryptography.md): The protocol signs, encrypts, or authenticates messages, or issues credentials.
- [Delay-tolerant networking](references/delay-tolerant-networking.md): Messages can take days to arrive, or pass through intermediaries that store them and forward them later.
- [Specifications](references/specifications.md): The protocol is being specified, or its specification changed.
