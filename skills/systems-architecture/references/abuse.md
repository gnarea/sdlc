# Denial of service and abuse

## Rate limits

- Every entry point reachable by untrusted parties MUST be rate-limited per client. The limit MUST apply per client identity as well as per IP address, because one attacker can spread their requests across many addresses (e.g., through residential proxies), and many legitimate clients can share one (e.g., behind a carrier's NAT).
- An abusive client MUST be throttled first, and MAY be blocked if the abuse persists.
- Where a client needn't be identified but its limits and reputation must follow it across addresses, they SHOULD be keyed on a pseudonym derived from a key pair that the client generates for this system alone, unless unlinkability is a requirement.
- Where the client is itself a server acting for an organisation, limits and blocks SHOULD be keyed on the organisation's domain name.

## Cheap identities

- A rate limit only caps what one identity can do. Where an attacker can come by identities cheaply (e.g., IP addresses through residential proxies, accounts that are free to create, peer identities that anyone can mint), each request or identity MUST also cost them something (e.g., a proof-of-work challenge, a humanity check, a payment).
- Legitimate clients and the environment bear that cost too, so it SHOULD rise with the system's load and fall with the reputation that the client has earned, and it MUST be affordable to the least capable client that the design supports (e.g., an old phone).
- A check that some supported clients or people can't pass (e.g., device attestation, a visual puzzle) MAY lower that cost, but MUST NOT be required.

## Exposure

- Where the cost of running the system scales with something an attacker controls, the design MUST bound it. Once reached, a bound denies service, so each MUST be set by weighing the bill against the outage.
- A component that no proxy can front (e.g., a peer in a peer-to-peer network) MUST mitigate protocol attacks itself, and SHOULD rely on a networking library to do so.
