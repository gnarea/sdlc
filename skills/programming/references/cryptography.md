# Cryptography

Generally, there MUST be a high-level wrapper that makes every unsafe use of a cryptographic primitive unspellable.

- Algorithms, curves, modes, and parameters MUST be selected from an enumerated set that omits everything deprecated or broken, so that a weak choice cannot be spelt.
- Where only one choice is defensible, it MUST be a constant rather than a parameter.
- Where interoperability forces a weak algorithm, it MUST be reachable only through a separately named operation whose name says so.
- A verification step MUST NOT be made optional. Where skipping it would be legitimate, offer a narrower operation rather than a flag, and record the refusal, along with what would change our mind.
- An empty or absent set of trust anchors MUST fail verification. The code MUST NOT guess whether the caller made a mistake or meant to skip the check.
- Private key material MUST NOT leave the store that holds it: sign and decrypt through the store's interface, never through an accessor that returns the key.
- Every key MUST have exactly one declared purpose, and MUST NOT be used for another.
- Keys, nonces, and identifiers MUST be drawn from the platform's cryptographic random source.
- Comparisons of secrets, authentication tags, and digests MUST be constant-time.
- A response from a cryptographic service MUST be verified before use: check integrity in both directions, and check that the answer refers to the key that was asked for.
- Validation performed when a credential is issued MUST be repeated when it's verified.
- Every parsed cryptographic structure MUST have an explicit byte limit, derived from the largest legitimate input, with the derivation commented.
- Cryptographic operations MUST NOT be mocked: tests MUST use real keys and real operations.
