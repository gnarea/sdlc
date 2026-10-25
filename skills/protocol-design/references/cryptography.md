# Cryptography

## Algorithms

- In each category (e.g., hashing, signing, key agreement, symmetric encryption), the protocol SHOULD only allow a closed set of algorithms.
- Exactly one algorithm in each category SHOULD be mandatory to implement. Others MAY be allowed alongside it, for those who need stronger guarantees than it offers.
- Broken or weak algorithms that implementations might still support (e.g., SHA-1, RSA keys under 2048 bits) MUST also be banned explicitly.
- These rules MUST extend to the algorithms that another algorithm uses internally (e.g., the hash function in a key derivation function).

## Verification

- Where a security property depends on a third party's answer (e.g., a DNS record), implementations SHOULD authenticate the answer themselves (e.g., by validating DNSSEC), rather than trust whoever relayed it (e.g., a resolver).
- Where the input to a verification admits more than one interpretation (e.g., two records that match the same key), verification MUST fail.

## Credentials and signatures

- The protocol MUST cap how long a credential can be valid, as low as its use cases allow, because wherever verifiers can't check for revocation, a compromised key remains usable until its credentials expire.
- A party MUST be able to hold more than one valid key or credential for the same purpose at a time (e.g., verifiers accept every credential that's still valid, a recipient keeps its previous key whilst messages encrypted with it can still arrive), so that rotating one doesn't require its peers to switch at the same time.
- A certificate MUST NOT be used where a raw key would do (e.g., an ephemeral key that the message carrying it already authenticates).
- Every signature MUST be bound to its purpose, through an identifier of the purpose in the signed content (e.g., an OID per message type), and verifiers MUST refuse a signature made for another purpose. Where a signature is meant for one recipient, it MUST also be bound to that recipient (e.g., through an audience).
