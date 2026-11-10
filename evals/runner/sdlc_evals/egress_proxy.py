"""HTTPS egress proxy that relays CONNECT tunnels to allowed hosts only.

TLS runs end to end through the tunnel, so the proxy sees the host name, the
timing, and the volume of each connection, and none of its content.
"""

import contextlib
import enum
import ipaddress
import selectors
import socket
import socketserver
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

HTTPS_PORT = 443
MAX_REQUEST_HEAD_BYTES = 8192
REQUEST_HEAD_DEADLINE = timedelta(seconds=10)
UPSTREAM_CONNECT_TIMEOUT = timedelta(seconds=10)
# A model's response can stream for as long as the harness lets a run last (one hour at most),
# with pauses whilst it thinks.
TUNNEL_IDLE_TIMEOUT = timedelta(minutes=15)
MAX_CONCURRENT_TUNNELS = 32
RELAY_CHUNK_BYTES = 65536
SHUTDOWN_POLL_INTERVAL = timedelta(milliseconds=50)

_LOOPBACK_ADDRESS = "127.0.0.1"
_HEAD_TERMINATOR = b"\r\n\r\n"


class RefusalReason(enum.StrEnum):
    """Why the proxy refused a connection."""

    HOST_NOT_ALLOWED = "host not allowed"
    PORT_NOT_ALLOWED = "port not allowed"
    NOT_CONNECT = "not a CONNECT request"
    MALFORMED_REQUEST = "malformed request"
    UPSTREAM_NOT_PUBLIC = "host resolves to a non-public address"
    TOO_MANY_TUNNELS = "too many concurrent tunnels"


@dataclass(frozen=True)
class Refusal:
    """A connection the proxy refused, with the host it asked for, if any."""

    time: datetime
    reason: RefusalReason
    host: str | None
    port: int | None


@dataclass(frozen=True)
class UpstreamFailure:
    """A connection to an allowed host that the proxy couldn't open."""

    time: datetime
    host: str
    error: str


@dataclass(frozen=True)
class _ConnectTarget:
    host: str
    port: int


class EgressProxy:
    """A CONNECT proxy on the loopback interface, which only tunnels to allowed hosts on port 443."""

    def __init__(
        self,
        server: socketserver.ThreadingTCPServer,
        thread: threading.Thread,
        log: _EventLog,
    ) -> None:
        self._server = server
        self._thread = thread
        self._log = log

    @classmethod
    def start(
        cls,
        allowed_hosts: frozenset[str],
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        resolve: Callable[[str, int], list[str]] | None = None,
        connect: Callable[[tuple[str, int], float], socket.socket] = socket.create_connection,
        request_head_deadline: timedelta = REQUEST_HEAD_DEADLINE,
    ) -> EgressProxy:
        """Listen on an ephemeral loopback port, and relay in a background thread until closed.

        `resolve`, `connect`, and `request_head_deadline` exist so that tests can stand in for the
        network and time.
        """
        log = _EventLog(now)
        policy = _TunnelPolicy(
            allowed_hosts=frozenset(_normalise_host(host) for host in allowed_hosts),
            resolve=resolve or _resolve,
            connect=connect,
            request_head_deadline=request_head_deadline,
            log=log,
            slots=threading.BoundedSemaphore(MAX_CONCURRENT_TUNNELS),
        )
        handler = type("_BoundHandler", (_TunnelHandler,), {"policy": policy})
        server = _Server((_LOOPBACK_ADDRESS, 0), handler)
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": SHUTDOWN_POLL_INTERVAL.total_seconds()},
            name="egress-proxy",
            daemon=True,
        )
        thread.start()
        return cls(server, thread, log)

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    @property
    def url(self) -> str:
        return f"http://{_LOOPBACK_ADDRESS}:{self.port}"

    def refusals(self) -> tuple[Refusal, ...]:
        return self._log.refusals()

    def upstream_failures(self) -> tuple[UpstreamFailure, ...]:
        return self._log.upstream_failures()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

    def __enter__(self) -> EgressProxy:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class _EventLog:
    def __init__(self, now: Callable[[], datetime]) -> None:
        self._now = now
        self._lock = threading.Lock()
        self._refusals: list[Refusal] = []
        self._upstream_failures: list[UpstreamFailure] = []

    def record_refusal(self, reason: RefusalReason, target: _ConnectTarget | None) -> None:
        refusal = Refusal(
            time=self._now(),
            reason=reason,
            host=target.host if target else None,
            port=target.port if target else None,
        )
        with self._lock:
            self._refusals.append(refusal)

    def record_upstream_failure(self, host: str, error: OSError) -> None:
        failure = UpstreamFailure(time=self._now(), host=host, error=type(error).__name__)
        with self._lock:
            self._upstream_failures.append(failure)

    def refusals(self) -> tuple[Refusal, ...]:
        with self._lock:
            return tuple(self._refusals)

    def upstream_failures(self) -> tuple[UpstreamFailure, ...]:
        with self._lock:
            return tuple(self._upstream_failures)


@dataclass(frozen=True)
class _TunnelPolicy:
    allowed_hosts: frozenset[str]
    resolve: Callable[[str, int], list[str]]
    connect: Callable[[tuple[str, int], float], socket.socket]
    request_head_deadline: timedelta
    log: _EventLog
    slots: threading.BoundedSemaphore


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = False


class _TunnelHandler(socketserver.BaseRequestHandler):
    policy: _TunnelPolicy

    def handle(self) -> None:
        client: socket.socket = self.request
        if not self.policy.slots.acquire(blocking=False):
            self.policy.log.record_refusal(RefusalReason.TOO_MANY_TUNNELS, None)
            _reply(client, 503, "Service Unavailable")
            return
        try:
            self._tunnel(client)
        finally:
            self.policy.slots.release()

    def _tunnel(self, client: socket.socket) -> None:
        head = _read_request_head(client, self.policy.request_head_deadline)
        if head is None:
            self.policy.log.record_refusal(RefusalReason.MALFORMED_REQUEST, None)
            _reply(client, 400, "Bad Request")
            return
        target_or_reason = _parse_connect(head)
        if isinstance(target_or_reason, RefusalReason):
            self.policy.log.record_refusal(target_or_reason, None)
            _reply(client, 405 if target_or_reason is RefusalReason.NOT_CONNECT else 400, "Refused")
            return
        target = target_or_reason
        refusal = self._authorise(target)
        if refusal is not None:
            self.policy.log.record_refusal(refusal, target)
            _reply(client, 403, "Forbidden")
            return
        upstream = self._connect_upstream(target)
        if upstream is None:
            _reply(client, 502, "Bad Gateway")
            return
        with upstream:
            _reply(client, 200, "Connection Established")
            _relay(client, upstream)

    def _authorise(self, target: _ConnectTarget) -> RefusalReason | None:
        if target.host not in self.policy.allowed_hosts:
            return RefusalReason.HOST_NOT_ALLOWED
        if target.port != HTTPS_PORT:
            return RefusalReason.PORT_NOT_ALLOWED
        return None

    def _connect_upstream(self, target: _ConnectTarget) -> socket.socket | None:
        # getaddrinfo() takes no timeout: the system resolver's own timeouts and attempts bound it.
        try:
            addresses = self.policy.resolve(target.host, target.port)
        except OSError as error:
            self.policy.log.record_upstream_failure(target.host, error)
            return None
        # Refusing every resolution unless all of them are public keeps an allowed name
        # from being pointed at the machine's own services.
        if not addresses or not all(
            ipaddress.ip_address(address).is_global for address in addresses
        ):
            self.policy.log.record_refusal(RefusalReason.UPSTREAM_NOT_PUBLIC, target)
            return None
        try:
            return self.policy.connect(
                (addresses[0], target.port), UPSTREAM_CONNECT_TIMEOUT.total_seconds()
            )
        except OSError as error:
            self.policy.log.record_upstream_failure(target.host, error)
            return None


def _resolve(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def _read_request_head(client: socket.socket, deadline_after: timedelta) -> bytes | None:
    deadline = time.monotonic() + deadline_after.total_seconds()
    head = b""
    while _HEAD_TERMINATOR not in head:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0 or MAX_REQUEST_HEAD_BYTES < len(head):
            return None
        client.settimeout(remaining_seconds)
        try:
            chunk = client.recv(MAX_REQUEST_HEAD_BYTES)
        except OSError:
            return None
        if not chunk:
            return None
        head += chunk
    # A client mustn't send tunnel data before the tunnel is established.
    if not head.endswith(_HEAD_TERMINATOR) or MAX_REQUEST_HEAD_BYTES < len(head):
        return None
    return head


def _parse_connect(head: bytes) -> _ConnectTarget | RefusalReason:
    try:
        request_line = head.split(b"\r\n", 1)[0].decode("ascii")
    except UnicodeDecodeError:
        return RefusalReason.MALFORMED_REQUEST
    parts = request_line.split(" ")
    if len(parts) != 3 or not parts[2].startswith("HTTP/1."):
        return RefusalReason.MALFORMED_REQUEST
    method, authority, _ = parts
    if method != "CONNECT":
        return RefusalReason.NOT_CONNECT
    host, separator, port_text = authority.rpartition(":")
    if not separator or not port_text.isdigit() or not host:
        return RefusalReason.MALFORMED_REQUEST
    port = int(port_text)
    if not 0 < port <= 65535:
        return RefusalReason.MALFORMED_REQUEST
    return _ConnectTarget(host=_normalise_host(host), port=port)


def _normalise_host(host: str) -> str:
    return host.strip().rstrip(".").lower()


def _reply(client: socket.socket, status: int, reason: str) -> None:
    # A client that has already gone needs no reply.
    with contextlib.suppress(OSError):
        client.sendall(f"HTTP/1.1 {status} {reason}\r\nContent-Length: 0\r\n\r\n".encode("ascii"))


def _relay(client: socket.socket, upstream: socket.socket) -> None:
    client.setblocking(False)
    upstream.setblocking(False)
    peers = {client: upstream, upstream: client}
    with selectors.DefaultSelector() as selector:
        for endpoint in peers:
            selector.register(endpoint, selectors.EVENT_READ)
        while True:
            ready = selector.select(timeout=TUNNEL_IDLE_TIMEOUT.total_seconds())
            if not ready:
                return
            for key, _ in ready:
                source: socket.socket = key.fileobj  # type: ignore[assignment]
                if not _forward(source, peers[source]):
                    return


def _forward(source: socket.socket, destination: socket.socket) -> bool:
    try:
        data = source.recv(RELAY_CHUNK_BYTES)
    except BlockingIOError:
        return True
    except OSError:
        return False
    if not data:
        return False
    destination.setblocking(True)
    destination.settimeout(TUNNEL_IDLE_TIMEOUT.total_seconds())
    try:
        destination.sendall(data)
    except OSError:
        return False
    finally:
        destination.setblocking(False)
    return True
