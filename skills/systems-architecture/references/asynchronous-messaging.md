# Asynchronous messaging

## Delivery

- The processing of a message MUST be idempotent, because the same message can be delivered more than once (e.g., when its acknowledgement is lost).
- Consumers MUST NOT depend on the order in which messages arrive: their state MUST converge whatever the order. Where only the latest message matters, the newest by creation date MUST win.
- Remote procedure calls MUST NOT be emulated. Where a sender needs the outcome of a message (e.g., the identifier of the account it asked for), the outcome MUST travel as a message of its own, and the sender MUST cope with it arriving late, more than once, out of order, or never.
- Where a message must cost its sender something (per the rules on abuse), the cost MUST be payable without a challenge from the recipient (e.g., a proof of work over public randomness).

## Expiry

- Every message MUST carry an expiry date, and every hop MUST enforce it on receipt and again before consuming it.
- Messages SHOULD be packaged for transport as late as possible, so that expired ones are left out.
- A record that guards against duplicates MUST be kept until the message it guards expires, and no longer.

## Failure

- Retries and dead-lettering MUST be configured on the broker, rather than implemented by the consumer. The consumer MUST only report whether a later attempt could succeed (e.g., in HTTP, `2xx` to acknowledge and `5xx` to have the broker redeliver).
- A message that can never be processed MUST be acknowledged, recorded, and discarded, so that its redelivery can't block the queue. In a batch, it MUST NOT prevent the rest from being processed.
- Duplicates are expected, and MUST be ignored without raising a warning.

## Brokers

- Messages SHOULD follow a standard envelope (e.g., CloudEvents), with an event type per meaning, even where two payloads happen to share a structure. Consumers SHOULD subscribe only to the types they handle.
- The broker SHOULD be the simplest one that meets the requirements, weighed against its operational burden, cost, and quotas.
- A message MUST fit in memory. Where a payload could exceed the broker's limit, it MUST be split, or kept in durable storage with only a reference sent through the broker.
- Where the broker doesn't persist messages (e.g., a non-durable pub/sub), it MUST only signal that new data is available. The subscriber MUST then fetch what's stored before following new signals.

## Scheduled work

- A schedule SHOULD publish a message that triggers the work, rather than run it directly. The work MUST then be driven by durable records that are deleted only once each item has succeeded or failed definitively, so that a later run picks up whatever an earlier one missed.
