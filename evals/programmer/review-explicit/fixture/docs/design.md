# Rate limiting for the partner API

## Problem

Last month, a partner integration with a retry bug sent 30,000 requests in ten minutes, and the database's connection pool ran out. Each API user should be limited to 600 requests per minute, and any request beyond that should be rejected with `429 Too Many Requests`.

## Context

- The partner API runs as a single process on `ThreadingHTTPServer`, from the standard library, which handles each request on a thread of its own.
- There are about 40 API users, one per partner integration.
- Counters may reset when the process restarts, since restarts are rare and the worst case is one extra window for each user.
- A fixed window lets a user send up to twice the limit across a window boundary, which still protects the connection pool.

## Design

A new module, `partner_api.ratelimit`, exposes one function:

```python
def allow(user_id: str, now: datetime) -> bool: ...
```

The request handler calls it once the request is authenticated, passing the current time, and responds with `429 Too Many Requests` when it returns `False`.

The module keeps one window per user in a module-level dictionary:

```python
REQUESTS_PER_MINUTE = 600


@dataclass
class Window:
    started_at: datetime
    count: int


_windows: dict[str, Window] = {}
```

`allow()` works as follows:

1. Look up the user's window in `_windows`, and create one that starts at `now` with a count of zero if there's none.
2. If the window started a minute or more before `now`, reset it to start at `now` with a count of zero.
3. If the count has reached `REQUESTS_PER_MINUTE`, return `False`.
4. Otherwise, increment the count and return `True`.

The dictionary holds at most one entry per API user, so it needs no eviction.

## Testing

Unit tests call `allow()` with explicit times, to cover a user under the limit, a user at the limit, and a user whose window has expired.
