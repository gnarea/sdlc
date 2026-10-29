# Cryptography

## Algorithms

- Each algorithm MUST be expected to stay secure for as long as the data it protects needs protecting (e.g., the period over which verifiers must accept a signature, or over which a ciphertext must stay confidential).
- Symmetric encryption MUST be authenticated (e.g., AES-GCM), so that a ciphertext that was tampered with fails to decrypt.
- A secret that wasn't generated as a key for its purpose (e.g., the output of a key agreement) MUST be passed through a key derivation function (e.g., HKDF) before it's used as one.

## Integrity

- Where a digest only has to detect accidental corruption (e.g., of a request to a key management service and its response, or of a file on disk), it SHOULD be a checksum (e.g., CRC32C), which is cheaper to compute and store than a cryptographic hash.
- Where an adversary could alter the data, but not the digest that it's checked against (e.g., a digest of a public key in a DNSSEC-signed record), the digest MUST come from a cryptographic hash function (e.g., SHA-256).
- Where an adversary could alter the digest too, a MAC or a signature MUST be used instead.
- Where data has to be signed or verified as it streams (e.g., a large upload), the signature algorithm MUST sign a digest of the data (e.g., Ed25519ph), and the hash function MUST be known before the data arrives.

## Keys

- Every key MUST have exactly one declared purpose, and MUST NOT be used for another.
- Private key material MUST NOT leave the store that holds it (e.g., a key management service, the platform's keystore): whatever needs a signature or a decryption MUST ask the store for it, rather than for the key. The store SHOULD hold its keys in hardware where the platform offers it (e.g., an HSM, a secure enclave).
- Algorithms SHOULD be chosen from those that the store supports, so that keys can stay in it. Where a key can't stay in the store (e.g., because the store doesn't support its algorithm, or a library needs the key itself, like a database passphrase), it MUST be encrypted at rest with a key that the store holds (aka _envelope encryption_).
- A private or secret key MUST NOT be embedded in an artefact that's distributed (e.g., a string literal in an app), since everyone who obtains the artefact obtains the key.
- A key that protects data in transit (e.g., a session key) MUST have a maximum lifetime, as short as its use allows, and MUST be deleted as soon as nothing in transit can still need it (e.g., a message encrypted with it that's yet to arrive), so that its compromise exposes as little traffic as possible.

## Randomness

- Keys, nonces, and identifiers MUST be drawn from the platform's cryptographic random source.

## Audits

- Where the system's security relies on cryptography, its design SHOULD be audited independently before it's implemented, and its implementation once it is, including the cryptographic libraries that it uses. Every report SHOULD be published in full.
