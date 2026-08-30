# End-user applications

Software installed on a device that the user controls. The device is neither trusted nor reliable.

## General

- Packages MUST be organised layer-first — domain, data, user interface, background work, and dependency injection — and the layout MUST be documented in the README.
- Functional tests MUST run on a matrix of real and virtual devices, spanning the oldest and the newest supported operating system versions.
- The product's vocabulary MUST be used in the user interface, and the domain's in the code, where the two differ. The mapping MUST be documented.

## Security and privacy

- The application MUST declare the fewest platform permissions it can function with, each justified in the README, and MUST NOT declare one for a capability delegated to another application.
- Automatic backup of application data MUST be disabled wherever that data includes keys or personal data.
- Telemetry, analytics, and crash reporting SHOULD NOT be compiled in by default.
- Encryption at rest MUST cover keys and credentials, rooted in the platform's keystore. It MUST also cover payloads, except where they are already encrypted end to end.
- Other processes on the device MUST be treated as untrusted, even where the user owns the device.

## Robustness

- The application MUST tolerate network delays and disruption. A user who is offline, or on an unreliable network, is the rule rather than the exception.
- The device is hostile to long-running work: a wait MUST be implemented as a short, repeated poll rather than a single long timer, so that it survives suspension and restart. Clock jumps MUST be tolerated.
- Durable state MUST be flushed to disc before the user is told that the work succeeded.
