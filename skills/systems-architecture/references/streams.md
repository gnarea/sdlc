# Streams

A stream is a long-lived connection (e.g., a WebSocket, a gRPC stream) that carries a series of items.

A stream SHOULD be used only where latency matters and the underlying channel is reliable.

## The connection

- Each side MUST detect a broken connection within a bounded time (e.g., through pings at a fixed interval), and drop it.
- The way a stream closes MUST tell the other side why (e.g., through a close code), including whether the operation completed and whether to reconnect.

## Bidirectional streams

- Acknowledgements MUST reference the individual delivery (e.g., a per-delivery identifier), rather than the item, and an acknowledgement for an unknown delivery MUST be treated as a protocol violation.
- The protocol MUST provide _back pressure_: the number of items that the recipient is still processing MUST be capped, and the sender MUST stop at the cap, either because the protocol requires it to or because the recipient tells it to slow down. A sender that exceeds the cap MAY be disconnected.
