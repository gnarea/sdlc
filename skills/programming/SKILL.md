---
name: programming
description: How code should be written regardless of language. Code organisation, naming, data modelling, error handling, security and privacy, and tests. Use when writing, changing, or reviewing source code.
---
# Programming

## Code organisation

- Modules MUST be partitioned by responsibility, using whichever decomposition is idiomatic for the software and its stack (e.g., layers such as domain, data, and UI in an application; capabilities in a library). The chosen decomposition MUST be applied uniformly, and MUST be documented in the README.
- Files SHOULD NOT exceed 800 LOC, including comments and blank lines. A file of 1 kLOC or more MUST be treated as a defect to fix.
- Everything that isn't part of a module's contract MUST use the strictest visibility the language offers.
- Entrypoints (e.g., `main`) MUST contain no logic of their own: they wire dependencies together and delegate.
- An abstraction MUST NOT be introduced for a second case that doesn't exist yet, and an extension point MUST NOT be built before something extends it.

## Functions, procedures, and the like

- Each MUST do one thing, at one level of abstraction, and SHOULD NOT exceed 40 LOC or a cyclomatic complexity of 10.
- Guard clauses and early returns SHOULD be used rather than nesting. An `else` on a failure path MUST NOT be used.
- A parameter list SHOULD NOT exceed seven parameters. Beyond that, they MUST be grouped into a type that names their relationship.
- An operation that can fail MUST NOT be exposed as a constructor: use a named factory instead (e.g., `deserialise`, `generate`).
- Comparisons SHOULD use `<`/`<=` rather than `>`/`>=`, so that the operands read from the lower bound to the upper bound (e.g., `if (MAX_TTL_SECONDS < ttl)`).
- Sources of non-determinism, such as the clock, randomness, and the scheduler or thread that work runs on, MUST be injected, so that a test can control them without a mock.

## Naming

- Constants, variables, fields, and the like SHOULD be named after what they hold, rather than what they are used for, and SHOULD match the taxonomy of the user interface and the programming interface.
- Functions, procedures, and the like MUST be named in the imperative (e.g., `submitResult`) or as questions (e.g., `wasResultSubmitted`).
- Booleans, and the functions that return them, MUST be prefixed with `is`, `has`, `are`, `can`, `do`/`does`/`did`, `should`, or `was`/`were`.
- Verbs MUST be used consistently across the codebase. For example: `make*` for factories, `init*` for constructors that read their input from the environment or a serialised form, `register*` for plugins, `configure*` for process-level side effects, and `require*` for guards that return nothing.
- `serialise`/`deserialise` MUST denote conversions to and from bytes, `encode`/`decode` conversions to and from structured representations, and `parse` conversions from strings.
- Generic type parameters MUST be whole words (e.g., `ResultType`), never single letters.
- Abbreviations MUST NOT be invented (e.g., `index`, not `i`). Only those already established in the domain or the platform MAY be used.
- A term MUST be defined once, and then used verbatim everywhere: code, tests, documentation, user-facing copy, and infrastructure.
- A rename whose only benefit is a better name MUST NOT be made where it would break a published surface.
- The user-facing vocabulary MAY differ from the code's, where the product hides a detail that the code must be precise about. Each MUST then be used consistently within its own domain, and the mapping MUST be documented.

## Data model

- Illegal states MUST be unrepresentable. A parameter that selects between behaviours MUST be an enum or a set of named factories, never a boolean; a value drawn from a closed set MUST be an enum, never a string.
- Invariants MUST be enforced where the value is constructed, so that an invalid instance cannot exist. Deserialisers MUST validate before constructing.
- Types MUST be immutable by default. Mutability MUST be confined to where it's needed, and MUST be evident in the type.
- The unit of a constant MUST be part of its name (e.g., `TOKEN_TTL_MINUTES`), unless the underlying data type abstracts the unit away (e.g., time deltas).

## Error handling

- Failures that the caller is expected to reason about MUST be returned as values (e.g., a result type carrying the reason). Programming errors and protocol violations MUST be raised.
- The cause MUST always be chained. Discarding a cause MUST be syntactically deliberate.
- Third-party errors MUST NOT escape the module that provoked them: catch them and re-raise them in the module's own vocabulary.
- The documentation of each error type MUST tell the caller what to do about it, starting with whether retrying is likely to help.
- Messages MUST state the expectation and the offending value (e.g., "TTL exceeds the maximum (got 3600)"), and MUST NOT carry secrets or personal data.
- Where a test asserts on the text of a message, that wording is part of what the module promises, and MUST NOT be reworded unless the meaning it conveys has changed.

## Reliability

- Every operation that can be repeated MUST be safe to repeat.
- Where a sequence of side effects cannot be atomic, it MUST be ordered so that a retry after any partial failure converges on the intended state, and a comment MUST explain why that order was chosen.
- Input that can never be processed successfully MUST be dropped and recorded, never retried.
- The process MUST be able to die at any point without corrupting what it owns, and MUST recover from durable state rather than from anything held in memory.
- Where the platform asks the process to stop (e.g., SIGTERM), the process MUST stop accepting work and exit within the grace period it's given.

## Security and privacy

### Trust boundaries

- Input crossing a trust boundary MUST be validated before use, including the responses of services we operate and of those we don't.
- Every untrusted input MUST have an explicit size limit, and every outbound call MUST have a timeout. Both MUST be named constants, and where the figure was derived rather than chosen, the derivation MUST be commented.
- A value that a security decision depends on MUST be re-validated wherever it re-enters the code, even where it was validated when it was issued.
- Where the input or the configuration is ambiguous or incomplete, the code MUST fail closed and refuse to proceed, rather than guess what was intended.
- A security control MUST NOT have an off switch. Where skipping it would be legitimate, offer a narrower operation that does less, rather than a flag that checks less.
- Secrets MUST NOT be written to disc, nor interpolated into a message. A credential scoped to a single run MUST be generated per run and held in memory.
- The software MUST request the fewest capabilities and permissions it can function with, and each MUST be justified in the README.

### Personal data

- Personal data MUST be collected only where a stated requirement needs it, and MUST be passed to the fewest modules that can do the job. It MUST NOT be carried in a context object that every layer can read.
- Retention MUST be enforced by the store that holds the data, never by a routine that can silently stop running.
- An identifier MUST NOT be given to a party that doesn't need it, especially where it would let that party correlate a person across contexts.
- Identifiers exposed to third parties MUST NOT be guessable, and MUST NOT leak the time or the volume of what they identify (e.g., a UUIDv4, rather than a sequential or timestamp-derived database ID).
- Telemetry, analytics, and crash reporting MUST NOT be added without explicit approval. Every host the software contacts MUST be enumerated in its documentation, with the reason.

## Dependencies and performance

- A new dependency, internal or external, MUST be justified against what the platform already offers. Where only an older, still-supported platform version lacks it, the code SHOULD degrade gracefully rather than take the dependency.
- The faster option MUST be taken where it costs nothing in clarity. Where clarity is traded away, the change MUST cite the measurement that justified it.
- Synchronous I/O MUST NOT block a path that serves a request or a user interface.
- Setup that only some code paths need MUST run when those paths run, rather than when the module loads. An implementation chosen at runtime, such as a storage or key-management adapter, MUST be loaded only after it has been chosen.

## Tests

- Every public/exported function, procedure, and the like MUST be unit tested against every branch a caller can provoke, every failure it documents, and both boundaries of every range it validates.
- Tests MUST assert on the values that a unit produces, rather than merely that it completed or returned a success status.
- Tests of the same unit whose arrange, act, and assert (AAA) blocks overlap substantially MUST be generated dynamically from data (aka _parameterised testing_).
- Where a parameterised suite supplies the unit under test as a case parameter, each case MUST assert something that distinguishes it from the others.
- **Private/internal** functions, procedures, and the like SHOULD NOT be unit tested directly: test them through the public/exported counterparts that use them. Where visibility is widened for testability, that concession MUST be documented on the member.
- Tests SHOULD use real dependencies, including databases and cryptographic operations, rather than test doubles. Where the real thing is used, each test run MUST get its own isolated instance or namespace.
- Test doubles MUST be confined to the I/O boundary and to sources of non-determinism. Mocks and spies MUST NOT be used to make one of our own units testable: a unit that needs them MUST be redesigned instead.
- Where a double is unavoidable, it MUST be a working implementation whose failures are injected explicitly, and whose state is exposed so that tests assert on outcomes rather than on interactions.
- A test that replaces a collaborator with a double MUST assert on the arguments that the double was given, because coverage doesn't check that a caller passes what the callee expects.
- Functional tests MUST exercise the deployed system over the network, MUST NOT import the code under test, MUST NOT touch backing services directly, and MUST NOT use mocks or spies.
- Functional tests MUST NOT contribute to the unit test measurements, so that the two signals stay separable.

## Comments

- You MUST NOT add or augment code comments unless the rationale for a particular block of code could not be inferred by carefully analysing the surrounding code. Typically, that means a workaround for an upstream bug (with a link to it), a spec ambiguity resolved one way rather than another, the derivation of a non-obvious constant, a deliberate trade-off, or the absence of code that a reader would expect to find.
- A comment MUST explain why the code is as it is, and MUST NOT paraphrase what it does.
- All comments MUST be succinct, and MUST NOT reference specific files/lines in the project.
- `TODO`, `FIXME`, and `HACK` markers MUST NOT be committed. Track the work in the issue tracker instead.
- A suppression of an automated check MUST be at the narrowest scope the tool offers, placed at the line it excuses, and MUST state its reason. Where the reason is an upstream defect, the suppression MUST link to it.

## Additional guidelines

Read a reference below where its condition holds; its rules apply in addition to the ones above.

### By artefact

- `references/libraries.md`: The repository publishes a package that other codebases depend on.
- `references/server-side-apps.md`: The repository produces a service that runs on infrastructure we operate, reached over a network.
- `references/end-user-apps.md`: The repository produces an application installed on a device the user controls, whether desktop or mobile.

### By concern

- `references/instrumentation.md`: The change adds, removes, or alters a diagnostic signal that the running process emits.
- `references/cryptography.md`: The change selects, configures, or invokes a cryptographic primitive, or handles a key, a credential, or a token.
- `references/prototyping.md`: The artefact is a throwaway prototype.
