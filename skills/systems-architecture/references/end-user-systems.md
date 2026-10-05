# End-user systems

## Topology

- Long-running work MUST live in a headless component that survives the user interface being closed, with the interface as its client.
- Where the interface reaches that component over a network interface, the channel MUST be authenticated with a credential that is only valid for that run. Where the channel runs over HTTP, including WebSocket, it MUST also refuse unauthorised web origins.

## Connectivity

- A reliable connection MUST NOT be taken for granted: work that needs the network MUST be queued durably.

## Security and privacy

- The application MUST declare the fewest platform permissions it can function with, each justified in the README, and MUST NOT declare one for a capability delegated to another application.
- Other processes on the device MUST be treated as untrusted, even where the user owns the device.
- Data MUST stay on the device unless a stated requirement needs it elsewhere.
- Telemetry, analytics, and crash reporting SHOULD NOT be compiled in by default.
- Telemetry MUST stay on the device unless the user opts in, and every destination MUST be documented.
- Encryption at rest MUST cover keys and credentials, rooted in the platform's keystore.
- Remote backups MUST NOT transmit or store sensitive data (e.g., cryptographic keys, personal data) in the clear.

## Storage

- Logs kept on the device MUST be rotated and capped in size, so that they can't fill its storage.

## Distribution

- Distribution MUST be part of the threat model, including a channel (e.g., an app store) removing or blocking the application.
