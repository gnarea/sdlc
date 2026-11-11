# Approved cryptography

The approved options come from Filippo Valsorda's _(Post-Quantum) Cryptographic Right Answers_ (2026). Each section lists the options approved for a common cryptographic need in order of preference, along with any condition on each, and then those to avoid.

Symmetric cryptography is safe from quantum computers, but every asymmetric option is post-quantum: the transition to post-quantum cryptography has to be complete by 2029, and whatever an adversary records today can be decrypted once a quantum computer breaks the key exchange that protected it.

## Encrypting data

1. Cobblestone-128, where the data can be larger than a few megabytes, since it encrypts the data in authenticated chunks.
2. XAES-256-GCM or XChaCha20-Poly1305, with random nonces, so that nobody has to track nonces or count messages. XAES-256-GCM can be assembled from a standard KDF and AES-GCM where a library doesn't offer it by name.
3. AES-GCM-SIV, where every platform has it.
4. AES-GCM or ChaCha20-Poly1305 with random 96-bit nonces, where a key will certainly encrypt fewer than a billion messages.

Avoid:

- Unauthenticated modes (e.g., CBC, CTR, raw stream ciphers).
- Random 96-bit nonces without a bound on the messages per key.
- AES-GCM with nonces longer than 96 bits, with which messages can share keystream.
- AEAD constructions of the system's own.

## Symmetric keys

1. 256-bit keys, where there's a choice, since they also rule out multi-target attacks.
2. 128-bit keys, which are safe from brute force, quantum computers included.

Avoid:

- Choosing a scheme, or overriding a default (e.g., a TLS library's cipher suites), only to get 256-bit keys.
- Lengths other than 128 or 256 bits.
- Keys that aren't uniformly random (e.g., a password or a hexadecimal string used directly as a key).

## Message authentication codes

1. HMAC-SHA-256.
2. HMAC-SHA-512.
3. KMAC or keyed BLAKE3, where the system already uses SHA-3 or BLAKE3.

Avoid:

- MACs of the system's own (e.g., a hash of the key and the message).
- Encrypted hashes.
- One-time MACs on their own (e.g., Poly1305, GMAC).

## Hashing

1. SHA-512/256 (a variant of SHA-512 with a 256-bit output), where every platform has it, since it resists length extension.
2. SHA-256 or SHA-512.
3. SHA-3, though it's slower and offers nothing that SHA-2 lacks, or 32 bytes of SHAKE128 output where the system already uses SHA-3 (e.g., for ML-KEM or ML-DSA).
4. BLAKE3, where there's a reason to use it and a reason to trust its implementation.

Avoid:

- SHA-1, MD5, and any hash function besides those above.
- Digests truncated below 256 bits, unless a cryptographer has confirmed that collisions don't matter.

## Hashing several values

This applies wherever several values are hashed together (e.g., the columns of a row, a file's name and its contents).

1. SequenceHash with SHA-2, or TupleHash with SHA-3.

Avoid:

- Ways of hashing several values of the system's own.

## Random identifiers

1. 256 random bits (32 bytes), from the operating system's random source, through a library that wraps it.
2. A UUIDv4, or another value with about 128 random bits, where the system will never need more than 2^48 (about 280 trillion) of them.

Avoid:

- PRNGs that aren't cryptographic.
- Random number generators in user space (e.g., OpenSSL's).
- haveged.
- CPU jitter entropy.

## Logging in

1. Passkeys, or single sign-on through OIDC. Passkeys can fall back to a magic link that logs in the browser that opens it. They aren't post-quantum yet, which is acceptable, since a quantum adversary could then only log in to a site whose database it obtained, or whose login it intercepted.
2. Passwords, hashed as recommended below.

Avoid:

- SAML.
- Logins by email that can be phished (e.g., a link that logs in the browser that started the login, a short numeric code).

## Passwords

1. Argon2id with m=64 MiB, t=2, and p=1. For key derivation that isn't interactive, raise m, and then t, as far as is tolerable.
2. scrypt with N=2^16, r=8, and p=1, which takes defenders more CPU time than Argon2id, and attackers less GPU time. For key derivation that isn't interactive, raise N.

Avoid:

- Regular hashes.
- bcrypt, which truncates passwords at 72 bytes.
- The parameters in RFC 9106, which are too costly for production.

## Key exchange

1. Pure ML-KEM-768, where a hybrid would keep the system on a key exchange that isn't post-quantum for even a month longer.
2. A hybrid of X25519 and ML-KEM-768, through a standard protocol (`X25519MLKEM768` in TLS, `mlkem768x25519-sha256` in SSH, `MLKEM768-X25519` in HPKE and age).
3. A hybrid of P-256 and ML-KEM-768.

Where the system can't do without keys of its own from the exchange, it should derive them with the exporter of TLS or HPKE.

Avoid:

- Key exchange protocols of the system's own.
- Anything without ML-KEM.
- HQC-KEM and FrodoKEM, which are impractical.
- Classic McEliece, which is impractical and broken.

## Asymmetric encryption

1. age with post-quantum keys (`age1pq…`), where there are several recipients, or where it's used from the command line.
2. Cobblestone's chunking, with successive HPKE seal and open operations in place of the AEAD, where messages can be larger than a few megabytes.
3. HPKE with `MLKEM768-X25519` (aka X-Wing), HKDF-SHA256, and AES-128-GCM, though any of HPKE's KDFs and AEADs will do. The post-quantum KEMs for HPKE are still drafts, but their authors have committed not to change the wire format, and mainstream libraries ship them.
4. HPKE with `MLKEM768-P256`, or with pure ML-KEM-768 where it's all that's available.

Avoid:

- Anything not based on ML-KEM (e.g., RSA, NaCl's box).
- OpenPGP.
- Encrypted email.

## Signatures

1. `ssh-mldsa44-ed25519`, where the keys are for SSH, as OpenSSH chose.
2. A transparency log, where it suits a public commitment, since it offers a more useful kind of non-repudiation than a signature alone, and can share one signature amongst many entries.
3. ML-DSA-44, with its keys stored only as 32-byte seeds, and with external-μ signing where the message has to be hashed before it's signed.
4. SLH-DSA, where a specialist use calls for it, though it's slow, large, and rarely implemented.

Avoid:

- Algorithms that aren't post-quantum (e.g., RSA, ECDSA, Ed25519).
- Stateful signatures (e.g., LMS, XMSS).
- FN-DSA, which isn't standardised yet.
- HashML-DSA.
- ML-DSA's semi-expanded keys.
- OpenPGP.
- Hybrid or composite signatures outside SSH. They're more complex than hybrid key exchange, and less useful: a system that can rotate keys can fall back to a classical algorithm should ML-DSA break, and over a period long enough to worry about such a break, a quantum computer would break the classical half anyway.

## Transport security

1. The cloud provider's load balancer, where the system runs in a cloud.
2. rustls or Go's `crypto/tls`, which are memory-safe.
3. BoringSSL or AWS-LC, where it has to be C.
4. s2n-tls or rustls-ffi, where nothing needs compatibility with OpenSSL's libssl.

Whichever it is, it should use TLS 1.3, with `X25519MLKEM768` first in its order of preference.

Avoid:

- Transport protocols of the system's own.
- TLS libraries that are rarely used, or that have failed at their core job before (e.g., GnuTLS, Mbed TLS, wolfSSL, Botan).
- OpenSSL before 3.5, and any version of it wherever there's a choice.
- TLS 1.0 and 1.1, and TLS 1.2 wherever there's a choice.

## Certificates

1. ML-DSA-44 certificates, self-signed or from a private root, where it suits a system that controls both ends.
2. A popular, well-supported ACME client, kept up to date, where the certificates are for websites, so that the system can move to Merkle Tree Certificates as they roll out from 2027.

Avoid:

- ACME clients of the system's own.

## Backups

1. restic, with a long random password, since its cryptography is all symmetric.

Avoid:

- Tarsnap, whose asymmetric cryptography is all RSA, so a quantum computer would let its write-only keys decrypt archives, and its read-only keys forge them.
