# Cryptographic right answers

What to use for each common cryptographic need, as of October 2026, along with what to consider, what's also fine, and what to avoid.

Symmetric cryptography is safe from quantum computers, but every asymmetric answer is post-quantum: the transition to post-quantum cryptography has to be complete by 2029, and whatever an adversary records today can be decrypted once a quantum computer breaks the key exchange that protected it.

## Encrypting data

- **Use**: the cloud provider's KMS, where the system runs in a cloud. Otherwise, XAES-256-GCM or XChaCha20-Poly1305, with random nonces, so that nobody has to track nonces or count messages. XAES-256-GCM can be assembled from a standard KDF and AES-GCM where a library doesn't offer it by name.
- **Use for data larger than a few megabytes, including where KMS holds the key**: Cobblestone-128, which encrypts the data in authenticated chunks.
- **Also fine**: AES-GCM-SIV, where every platform has it. AES-GCM or ChaCha20-Poly1305 with random 96-bit nonces, only where a key will certainly encrypt fewer than a billion messages.
- **Avoid**: unauthenticated modes (e.g., CBC, CTR, raw stream ciphers); random 96-bit nonces without a bound on the messages per key; AES-GCM with nonces longer than 96 bits, with which messages can share keystream; and AEAD constructions of the system's own.

## Symmetric keys

- **Use**: 256-bit keys, where there's a choice.
- **Also fine**: 128-bit keys, which are safe from brute force, quantum computers included, whereas 256-bit keys also rule out multi-target attacks.
- **Avoid**: choosing a scheme, or overriding a default (e.g., a TLS library's cipher suites), only to get 256-bit keys; lengths other than 128 or 256 bits; and keys that aren't uniformly random (e.g., a password or a hexadecimal string used directly as a key).

## Message authentication codes

- **Use**: HMAC-SHA-256.
- **Also fine**: HMAC-SHA-512. KMAC or keyed BLAKE3, where the system already uses SHA-3 or BLAKE3.
- **Avoid**: MACs of the system's own (e.g., a hash of the key and the message); encrypted hashes; and one-time MACs on their own (e.g., Poly1305, GMAC).

## Hashing

- **Use**: SHA-512/256 where every platform has it, since it resists length extension. Otherwise, SHA-256 or SHA-512.
- **Use for several values at once** (e.g., the columns of a row, a file's name and its contents): SequenceHash with SHA-2, or TupleHash with SHA-3.
- **Also fine**: SHA-3, though it's slower and offers nothing that SHA-2 lacks, and 32 bytes of SHAKE128 output where the system already uses SHA-3 (e.g., for ML-KEM or ML-DSA). BLAKE3, only with a reason to use it and a reason to trust its implementation.
- **Avoid**: SHA-1, MD5, and any hash function besides those above; ways of hashing several values of the system's own; and digests truncated below 256 bits, unless a cryptographer has confirmed that collisions don't matter.

## Random identifiers

- **Use**: 256 random bits (32 bytes), from the operating system's random source (`getrandom` on Linux, `ProcessPrng` on Windows, `arc4random_buf` on macOS and BSD, `getRandomValues` on the Web), through a library that wraps it.
- **Also fine**: a UUIDv4, or another value with about 128 random bits, unless the system needs more than 2^48 (about 280 trillion) of them.
- **Avoid**: PRNGs that aren't cryptographic; random number generators in user space (e.g., OpenSSL's); haveged; and CPU jitter entropy.

## Passwords

- **Use for logging in**: passkeys, rather than passwords. Passkeys aren't post-quantum yet, which is acceptable, since a quantum adversary could then only log in to a site whose database it obtained, or whose login it intercepted.
- **Consider for logging in**: a magic link that logs in the browser that opens it, as the fallback to passkeys. Single sign-on through OIDC.
- **Use where a password is needed**: Argon2id with m=64 MiB, t=2, and p=1. For key derivation that isn't interactive, raise m, and then t, as far as is tolerable.
- **Also fine**: scrypt with N=2^16, r=8, and p=1, which takes defenders more CPU time than Argon2id, and attackers less GPU time. For key derivation that isn't interactive, raise N.
- **Avoid**: regular hashes; bcrypt, which truncates passwords at 72 bytes; the parameters in RFC 9106, which are too costly for production; SAML; and logins by email that can be phished (e.g., a link that logs in the browser that started the login, a short numeric code).

## Key exchange

- **Use**: a standard protocol with a hybrid of X25519 and ML-KEM-768 (`X25519MLKEM768` in TLS, `mlkem768x25519-sha256` in SSH, `MLKEM768-X25519` in HPKE and age). Where the system can't do without keys of its own from the exchange, derive them with the exporter of TLS or HPKE.
- **Use where a hybrid would keep the system on a key exchange that isn't post-quantum for even a month longer**: pure ML-KEM-768.
- **Also fine**: P-256 with ML-KEM-768.
- **Avoid**: key exchange protocols of the system's own; anything without ML-KEM; HQC-KEM and FrodoKEM, which are impractical; and Classic McEliece, which is impractical and broken.

## Asymmetric encryption

- **Use**: HPKE with `MLKEM768-X25519` (aka X-Wing), HKDF-SHA256, and AES-128-GCM. The post-quantum KEMs for HPKE are still drafts, but their authors have committed not to change the wire format, and mainstream libraries ship them.
- **Use for several recipients, or from the command line**: age with post-quantum keys (`age1pq…`).
- **Use for messages larger than a few megabytes**: Cobblestone's chunking, with successive HPKE seal and open operations in place of the AEAD.
- **Also fine**: `MLKEM768-P256` as the KEM, or pure ML-KEM-768 where it's all that's available. Any of HPKE's KDFs and AEADs.
- **Avoid**: anything not based on ML-KEM (e.g., RSA, NaCl's box); OpenPGP; and encrypted email.

## Signatures

- **Use**: ML-DSA-44, with its keys stored only as 32-byte seeds. Where the message has to be hashed before it's signed, external-μ signing.
- **Use for SSH keys**: `ssh-mldsa44-ed25519`, as OpenSSH chose.
- **Consider for public commitments**: a transparency log, which offers a more useful kind of non-repudiation than a signature alone, and can share one signature amongst many entries.
- **Also fine**: SLH-DSA for specialist uses, though it's slow, large, and rarely implemented.
- **Avoid**: algorithms that aren't post-quantum (e.g., RSA, ECDSA, Ed25519); stateful signatures (e.g., LMS, XMSS); FN-DSA, which isn't standardised yet; HashML-DSA; ML-DSA's semi-expanded keys; OpenPGP; and hybrid or composite signatures outside SSH. Hybrid signatures are more complex than hybrid key exchange, and less useful: a system that can rotate keys can fall back to a classical algorithm should ML-DSA break, and over a horizon long enough to worry about such a break, a quantum computer would break the classical half anyway.

## Transport security

- **Use**: the cloud provider's load balancer, where the system runs in a cloud, with a post-quantum security policy where it needs one. Otherwise, rustls or Go's `crypto/tls`, which are memory-safe, or BoringSSL or AWS-LC where it has to be C (the latter has versioned releases).
- **Use for the key exchange**: TLS 1.3, with `X25519MLKEM768` first in the order of preference. On RHEL 9 and its derivatives, it has to be turned on.
- **Use for the certificates of websites**: a popular, well-supported ACME client, kept up to date, so that the system can move to Merkle Tree Certificates as they roll out from 2027.
- **Consider for certificates where the system controls both ends**: ML-DSA-44 certificates, self-signed or from a private root.
- **Also fine**: s2n-tls or rustls-ffi, where nothing needs compatibility with OpenSSL's libssl.
- **Avoid**: transport protocols and ACME clients of the system's own; TLS libraries that are rarely used, or that have failed at their core job before (e.g., GnuTLS, Mbed TLS, wolfSSL, Botan); OpenSSL before 3.5, and any version of it wherever there's a choice; TLS 1.0 and 1.1; and TLS 1.2 wherever there's a choice.

## Backups

- **Use**: restic, with a long random password, since its cryptography is all symmetric.
- **Avoid**: Tarsnap, whose asymmetric cryptography is all RSA, so a quantum computer would let its write-only keys decrypt archives, and its read-only keys forge them.
