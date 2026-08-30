# Server-side applications

## Configuration

- Configuration MUST be loaded and validated at start-up, and a missing required value MUST cause the process to exit with an error.
- The server's configuration MUST NOT change during its lifetime; reading it exactly once is the simplest way to guarantee that.
- Each configuration option SHOULD be represented by an environment variable. Configuration files SHOULD NOT be used.

## Runtime

- Every failure that crosses the network boundary MUST map to a stable problem identifier, and the mapping MUST be exhaustive, so that adding a failure mode fails the build until it's mapped.
- Where the system ships a client library, functional tests MUST drive the system through it, so that they double as contract tests for that library.

## Interchangeable backing services

- Where the application can work with more than one provider of the same thing (e.g., S3 or GCS for object storage), each MUST be reached through a single interface of our own.
- That interface MUST offer only what every provider can do. An operation that one provider supports and another doesn't MUST NOT be added to it.
- Where providers disagree on a detail (e.g., deleting an object that isn't there succeeds on one and fails on another), the adapter MUST hide the difference, and the behaviour settled on MUST be documented on the interface.
- Functional tests MUST run against one of the real providers, rather than a stand-in written for testing, so that the code path used by anyone who deploys it that way cannot rot.
