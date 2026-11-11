# Cryptography

## Algorithms

- In each category (e.g., hashing, signing, key agreement, symmetric encryption), the protocol SHOULD only allow a closed set of algorithms.
- Exactly one algorithm in each category SHOULD be mandatory to implement. Others MAY be allowed alongside it, for those who need stronger guarantees than it offers.
- Broken or weak algorithms that implementations might still support (e.g., SHA-1, RSA keys under 2048 bits) MUST also be banned explicitly.
- These rules MUST extend to the algorithms that another algorithm uses internally (e.g., the hash function in a key derivation function).

## Verification

- Where a security property depends on a third party's answer (e.g., a DNS record), implementations SHOULD authenticate the answer themselves (e.g., by validating DNSSEC), rather than trust whoever relayed it (e.g., a resolver).
- Where the input to a verification admits more than one interpretation (e.g., two records that match the same key), verification MUST fail.

## Keys, credentials, and signatures

- A party MUST be able to hold more than one valid key or credential for the same purpose at a time (e.g., verifiers accept every credential that's still valid, a recipient keeps its previous key whilst messages encrypted with it can still arrive), so that rotating one doesn't require its peers to switch at the same time.
- A key that protects messages in transit (e.g., a session key) MUST have a maximum lifetime, as short as its use cases allow, and MUST be deleted as soon as no message encrypted with it can still arrive, so that its compromise exposes as little traffic as possible.
- A certificate MUST NOT be used where a raw key would do (e.g., an ephemeral key that the message carrying it already authenticates).
- Where intermediaries relay a message that's encrypted end-to-end past them, the message MUST be signed after it's encrypted, so that each of them can verify the signature without decrypting it.
- Where a message is authenticated in chunks (e.g., a large file), everything that the recipient needs to verify a chunk (e.g., the algorithms, the signature that covers the chunk) MUST come before that chunk, so that the recipient can verify each one as it arrives.
