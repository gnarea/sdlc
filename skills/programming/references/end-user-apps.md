# End-user applications

Software installed on a device that the user controls. The device is neither trusted nor reliable.

## General

- Packages MUST be organised layer-first — domain, data, user interface, background work, and dependency injection — and the layout MUST be documented in the README.
- Functional tests MUST run on a matrix of real and virtual devices, spanning the oldest and the newest supported operating system versions.
- The product's vocabulary MUST be used in the user interface, and the domain's in the code, where the two differ. The mapping MUST be documented.

## Robustness

- A user who is offline, or on an unreliable network, is the rule rather than the exception: work that is waiting for the network MUST be presented as pending rather than failed, without requiring user intervention.
- The device is hostile to long-running work: a wait MUST be implemented as a short, repeated poll rather than a single long timer, so that it survives suspension and restart. Clock jumps MUST be tolerated.
- Durable state MUST be flushed to disc before the user is told that the work succeeded.
- What the user sees MUST be recomputed from durable state, rather than driven by whichever event arrived, so that late and out-of-order updates converge.
