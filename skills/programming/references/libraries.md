# Published libraries

The contract is the product.

## Public surface

- Everything outside the public surface MUST carry the strictest visibility the language offers, and the language's explicit-API mode MUST be enabled where one exists.
- Every public member MUST carry a doc comment, and the build MUST fail on an undocumented one.
- A type that callers must be able to catch or refer to, but never create themselves — an exception class, typically — SHOULD be closed to both instantiation and subclassing from outside the library (e.g., through an internal constructor).
- The verbs that build an instance MUST come from one small set, reused across the whole library — `init`, `initFrom*`, `deserialise`, `generate`, `issue`, `sign`, `retrieve` — so that a caller who has learnt one type can guess how to build the rest. A new verb MUST NOT be coined where one of those fits.
- Where the library lets callers supply their own implementation of something, a check that must always run MUST live in a public method that cannot be overridden, and that method MUST call the overridable one. A faulty implementation can then still return the wrong answer, but it cannot skip the check (e.g., a caller's key store cannot hand back an expired certificate).
- A capability MUST NOT be added to an abstraction unless every implementation can support it in a normalised way.
- A dependency's types MUST NOT appear in the public surface.

## Testing

- Test doubles that consumers will need MUST ship inside the library, held to the same standards as the rest of it.
- Tests MUST run against the oldest platform version that the library claims to support, and on every operating system it claims to support.
