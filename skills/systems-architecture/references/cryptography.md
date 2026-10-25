# Cryptography

- Every key MUST have exactly one declared purpose, and MUST NOT be used for another.
- Private key material MUST NOT leave the store that holds it (e.g., a key management service, the platform's keystore): whatever needs a signature or a decryption MUST ask the store for it, rather than for the key.
- Keys, nonces, and identifiers MUST be drawn from the platform's cryptographic random source.
