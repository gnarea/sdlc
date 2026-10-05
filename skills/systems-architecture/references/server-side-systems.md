# Server-side systems

## Topology

- Instances MUST be stateless and interchangeable, so that the platform can start and stop them at will.
- Administrative tasks MUST run in dedicated instances of the component that are unreachable from the Internet.
- Every instance MUST declare limits on the resources it can consume (e.g., CPU, memory), and MUST run with no more operating system privileges than it needs (e.g., as an unprivileged user, on a read-only filesystem).

## Configuration

- Each configuration option SHOULD reach an instance as an environment variable. Configuration files SHOULD NOT be used.

## Health checks

- A liveness check MUST NOT check a backing service, because a restart can't fix a dependency.
- A readiness check MUST check only what is local to the instance, because a failed shared dependency would take every instance out of rotation at once.
- A check of shared dependencies SHOULD be exposed for monitoring, but MUST NOT be able to restart the instance or take it out of rotation.

## Denial of service

- Where the threat model includes denial of service, a server reachable from the Internet MUST sit behind a reverse proxy run by a provider built to absorb volumetric and protocol attacks. Where the proxy may read the traffic, it SHOULD filter application attacks too; where it may not, the design MUST record what is left to our own code (e.g., TLS exhaustion).
- Where a proxy shields a server, the server MUST be reachable only through it. Where the server can't be taken off the Internet, it MUST accept traffic only from the proxy, and its address MUST be hard to guess.
- A rate limit MUST hold across instances: enforce it where all the traffic passes (e.g., a gateway), or count in a store that the instances share.
- Content that is the same for every client SHOULD be served from a managed store (e.g., an object store) and cached at the proxy, so that a flood of requests never reaches our compute.
- The number of instances MUST be capped, so that an attack can't scale the bill without bound.

## Data

- Indices MUST be specified with the schema, including the uniqueness constraints that make retries safe and the expiry that enforces retention.

## Keys

- A long-term private key MUST be generated and used inside a key management service, backed by hardware where the provider offers it, so that the key never reaches an instance.
