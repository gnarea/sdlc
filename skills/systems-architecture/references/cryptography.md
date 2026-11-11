# Cryptography

## Algorithms

- Each algorithm MUST be expected to stay secure for as long as the data it protects needs protecting (e.g., the period over which verifiers must accept a signature, or over which a ciphertext must stay confidential).
- Each algorithm, scheme, protocol, and library SHOULD be one of the options that the approved cryptography lists for its need. It MUST NOT be one that the approved cryptography says to avoid, unless a compliance regime that the system must meet (e.g., CNSA 2.0), or a third party that it must interoperate with, requires it.
- Where a digest only has to detect accidental corruption (e.g., of a file on disk), it SHOULD be a checksum (e.g., CRC32C), which is cheaper to compute and store than a cryptographic hash.

## Keys

- Every key MUST have exactly one declared purpose, and MUST NOT be used for another.
- Every key that has to stay secret, whether symmetric or private, MUST be generated inside the store that holds it (e.g., a key management service, the platform's keystore), backed by hardware where the store offers it, and MUST NOT leave it: whatever needs the key MUST ask the store to use it (e.g., to sign, decrypt, or compute a MAC). Algorithms MUST therefore be chosen from those that the store supports, and a store that supports none of those that the approved cryptography allows for the job SHOULD NOT be used.
- The only keys that MAY be held outside the store are those for a job that the store can't do (e.g., an ephemeral key in a key agreement, a database passphrase that a library needs). Wherever such a key is stored, it MUST be encrypted with a key that the store holds (aka _envelope encryption_). Where the key is outside the store only because the store lacks its algorithm, the design MUST instead assess whether envelope encryption has any merit.
- The shared secret from a key agreement MUST NOT be used as a key: each key MUST be derived from it with a KDF (e.g., HKDF, the exporter of TLS or HPKE).
- Keys, nonces, and identifiers MUST be drawn from the platform's cryptographic random source.

## Authentication

- A signature MUST only be used where its verifiers can't share a secret with its signer (e.g., third parties verify it offline). Otherwise, a MAC, or a random token that the issuer looks up, MUST be used instead (e.g., a session token, rather than a signed JWT).
- Whatever is signed, MACed, or encrypted MUST be bound to the context that it's meant for, and verifiers MUST refuse it in any other. Its context comprises whichever of these apply: its purpose (e.g., the operation that it authorises, the service that it's for), the type and version of its format (even where they travel as metadata), its parties (e.g., its recipient), whatever it belongs to (e.g., the identifier of a user's record, so that a ciphertext from one record doesn't decrypt as part of another), and, for a chunk of a larger whole, its position and whether it's the last one.
- The context MUST be bound through the signed or MACed content for a signature or a MAC, and through the KDF's input for a derived key (e.g., the direction of the traffic that the key protects, so that two peers don't derive the same key for both directions). A ciphertext MUST be bound through the input that its scheme binds it to (e.g., an AEAD's additional data, Cobblestone's context), even where a signature around it covers the context, since anyone who can sign could wrap the same ciphertext in a signature of their own. Only where the scheme takes no such input (e.g., age) MAY the context go inside the plaintext instead, for the recipient to check once it's decrypted.
- Where several values are authenticated together (e.g., signed, MACed, or passed to an AEAD as additional data), they MUST be encoded so that they can only be read one way (e.g., in a DER `SEQUENCE`), and MUST NOT be concatenated.
- A signature or a MAC MUST be verified over the exact bytes that the sender authenticated, as they were received, and the recipient MUST use nothing but what it parses from those bytes. It MUST NOT parse the content and serialise it again to verify it, even in an encoding that's meant to be canonical (e.g., DER), so the format MUST carry the bytes as they were authenticated (e.g., as the encapsulated content of a CMS `SignedData`).
- Whatever a party has to authenticate MUST NOT be processed, stored, or forwarded until it's verified. Content too large to hold in memory MUST therefore be authenticated in chunks, each of which is verified before it's used (e.g., with Cobblestone, for encryption), and whatever depends on the content as a whole (e.g., acknowledging it, committing it to storage) MUST wait until every chunk is verified.
