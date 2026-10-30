# Cryptography

- Each algorithm MUST be expected to stay secure for as long as the data it protects needs protecting (e.g., the period over which verifiers must accept a signature, or over which a ciphertext must stay confidential).
- Where a digest only has to detect accidental corruption (e.g., of a file on disk), it SHOULD be a checksum (e.g., CRC32C), which is cheaper to compute and store than a cryptographic hash.
- Every key MUST have exactly one declared purpose, and MUST NOT be used for another.
- Private key material MUST be generated inside the store that holds it (e.g., a key management service, the platform's keystore), backed by hardware where the store offers it, and MUST NOT leave it: whatever needs a signature or a decryption MUST ask the store for it, rather than for the key.
- Algorithms SHOULD be chosen from those that the store supports, so that keys can stay in it. Where a key can't stay in the store (e.g., because the store doesn't support its algorithm, or a library needs the key itself, like a database passphrase), it MUST be encrypted at rest with a key that the store holds (aka _envelope encryption_).
- Keys, nonces, and identifiers MUST be drawn from the platform's cryptographic random source.
