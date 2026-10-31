# Server-side applications

## Configuration

- Configuration MUST be loaded and validated at start-up, and a missing required value MUST cause the process to exit with an error.
- The server's configuration MUST NOT change during its lifetime; reading it exactly once is the simplest way to guarantee that.

## Runtime

- Every failure that crosses the network boundary MUST be mapped to its identifier in the contract, and the mapping MUST be exhaustive, so that adding a failure mode fails the build until it's mapped.
- Where the system ships a client library, functional tests MUST drive the system through it, so that they double as contract tests for that library.

## Interchangeable backing services

- Where the application can work with more than one provider of the same thing (e.g., S3 or GCS for object storage), each MUST be reached through a single interface of our own.
- That interface MUST offer only what every provider can do. An operation that one provider supports and another doesn't MUST NOT be added to it.
- Where providers disagree on a detail (e.g., deleting an object that isn't there succeeds on one and fails on another), the adapter MUST hide the difference, and the behaviour settled on MUST be documented on the interface.

## Tenancy

Where the application serves more than one _tenant_ (e.g., each customer organisation of a SaaS product):

- A resource that tenants share (e.g., a database table, an object store bucket) MUST be reachable only through an interface that is bound to specific tenants when it's constructed (e.g., a repository whose factory takes a tenant's identifier and adds it to every query), so that no call through it can reach another tenant's data.
- That interface MUST be bound to a single tenant, unless the operation is meant to span tenants (e.g., a billing run), in which case it MUST be bound to the tenants that the operation covers.
