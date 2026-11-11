# Synchronous messaging

Request-response MUST be limited to operations that complete within seconds. Anything slower MUST be handed to a broker, with the response saying only that the request was accepted (e.g., `202 Accepted`).

## Responses

- A response MUST tell the client whether to retry: the request succeeded or was deliberately dropped, the same request will never succeed, or it may succeed later (e.g., 2xx, 4xx, and 5xx respectively in HTTP).
- A failed upstream dependency MUST be reported as our failure, and as one that may succeed later (e.g., `503 Service Unavailable` in HTTP).
- A failure that is ours MUST NOT reveal anything about the server's internals.

## The client

- Every request MUST have a short, explicit timeout that the caller can override. A client's timeout MUST be shorter than that of whoever called it.
- A client MUST honour a server's instruction to slow down, including for how long (e.g., `429 Too Many Requests` and `Retry-After` in HTTP).
- A client that calls the same dependency repeatedly SHOULD stop calling it after consecutive failures, and probe it at intervals until it recovers (aka _circuit breaking_), so that a struggling dependency isn't overwhelmed and callers fail fast.

## The server

- An operation that changes state (e.g., a `POST` in HTTP) MUST be idempotent, because the client may retry it.
- Where a client must authenticate, the request MUST carry a short-lived credential bound to the server (e.g., a JWT whose audience is the server URL), and the server MUST NOT keep a session.
