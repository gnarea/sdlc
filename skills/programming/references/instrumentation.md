# Instrumentation

Instrumentation MUST be emitted through a vendor-neutral API, with the exporter chosen at start-up and hidden behind an adapter, so that no vendor's types appear elsewhere. A library MUST leave that choice to the application embedding it.

On a device the user controls, telemetry data MUST stay on the device unless the user opts in. Every destination MUST be documented.

## Logs

- Logs MUST be structured: the message is a constant string, and everything variable is a field.
- The level MUST be chosen by what the event asks of whoever keeps the software working, rather than by how serious it feels:
  - `debug`: Relevant only during development or debugging.
  - `info`: Nothing is wrong. Worth recording because it explains later behaviour, such as an outcome observable outside the process, or an unusual interaction with a dependency.
  - `warn`: Something went wrong and the software absorbed it, so nobody was denied what they asked for. It needs attention, but not now.
  - `error`: Something went wrong that the software could not absorb, so a user or a caller was denied what they asked for. It needs attention at once.
  - `fatal`: The process cannot continue, and is terminating.
- Field names MUST be consistent across the codebase, because they are the only thing a query can join on.
- Fields shared by more than one message SHOULD be documented, along with what each one lets an operator trace.
- Every decision to refuse, drop, or degrade MUST be logged exactly once, with the reason as a field.
- A failure MUST be logged where its outcome is decided, and MUST NOT be logged again at each level it propagates through.
- Personally identifiable data SHOULD NOT be logged above `debug`, and secrets MUST NOT be logged at all.
- Message strings and field names are what an operator greps and an alert matches. Where a test or an alert matches on one, it SHOULD NOT be reworded unless the meaning it conveys has changed.

## Metrics

- A metric MUST NOT be added unless the alert or the decision that consumes it has been identified.
- Every label MUST be drawn from a bounded set. Identifiers, addresses, and free text MUST NOT be labels.
- A name MUST carry its unit, and a duration MUST be recorded as a distribution rather than an average.

## Traces

- A span MUST be started only at a boundary: an incoming request, job, command, or user action; or a call that leaves the process. Elsewhere, propagating the context MUST be the only tracing concern.
- Sampling MUST be decided once, where the trace starts, and a trace that ends in a failure MUST be kept regardless.
- A log emitted inside a span MUST carry the trace and span identifiers.
