import socket
import threading
import unittest
from datetime import UTC, datetime, timedelta

from sdlc_evals.egress_proxy import EgressProxy, RefusalReason

PUBLIC_ADDRESS = "93.184.215.14"
NOW = datetime(2026, 11, 9, tzinfo=UTC)


class _EchoServer:
    """A loopback server that echoes what it receives, standing in for the upstream host."""

    def __init__(self) -> None:
        self.server = socket.create_server(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self) -> None:
        connection, _ = self.server.accept()
        with connection:
            while data := connection.recv(1024):
                connection.sendall(data)

    def close(self) -> None:
        self.server.close()


class EgressProxyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.echo = _EchoServer()
        self.connections: list[tuple[tuple[str, int], float]] = []
        self.resolutions: list[tuple[str, int]] = []

    def tearDown(self) -> None:
        self.echo.close()

    def _start(self, addresses: list[str] | None = None, **options: object) -> EgressProxy:
        def resolve(host: str, port: int) -> list[str]:
            self.resolutions.append((host, port))
            return [PUBLIC_ADDRESS] if addresses is None else addresses

        def connect(address: tuple[str, int], timeout: float) -> socket.socket:
            self.connections.append((address, timeout))
            return socket.create_connection(self.echo.server.getsockname()[:2], timeout=timeout)

        proxy = EgressProxy.start(
            frozenset({"api.anthropic.com"}),
            now=lambda: NOW,
            resolve=resolve,
            connect=connect,
            **options,
        )
        self.addCleanup(proxy.close)
        return proxy

    def _request(self, proxy: EgressProxy, request: bytes) -> tuple[socket.socket, bytes]:
        client = socket.create_connection(("127.0.0.1", proxy.port), timeout=5)
        self.addCleanup(client.close)
        client.sendall(request)
        reply = b""
        while b"\r\n\r\n" not in reply:
            chunk = client.recv(1024)
            if not chunk:
                break
            reply += chunk
        return client, reply

    def test_tunnels_to_an_allowed_host_on_its_resolved_public_address(self) -> None:
        proxy = self._start()

        client, reply = self._request(
            proxy, b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nHost: api.anthropic.com\r\n\r\n"
        )
        client.sendall(b"ping")

        self.assertTrue(reply.startswith(b"HTTP/1.1 200 "))
        self.assertEqual(client.recv(4), b"ping")
        self.assertEqual(self.resolutions, [("api.anthropic.com", 443)])
        self.assertEqual(self.connections, [((PUBLIC_ADDRESS, 443), 10.0)])
        self.assertEqual(proxy.refusals(), ())

    def test_normalises_the_host_before_matching_it(self) -> None:
        proxy = self._start()

        _, reply = self._request(proxy, b"CONNECT API.Anthropic.COM.:443 HTTP/1.1\r\n\r\n")

        self.assertTrue(reply.startswith(b"HTTP/1.1 200 "))
        self.assertEqual(self.resolutions, [("api.anthropic.com", 443)])

    def test_refuses_and_records_requests_it_must_not_relay(self) -> None:
        cases = [
            (
                b"CONNECT example.com:443 HTTP/1.1\r\n\r\n",
                b"403",
                RefusalReason.HOST_NOT_ALLOWED,
                "example.com",
                443,
            ),
            (
                b"CONNECT api.anthropic.com:80 HTTP/1.1\r\n\r\n",
                b"403",
                RefusalReason.PORT_NOT_ALLOWED,
                "api.anthropic.com",
                80,
            ),
            (
                b"GET http://api.anthropic.com/ HTTP/1.1\r\n\r\n",
                b"405",
                RefusalReason.NOT_CONNECT,
                None,
                None,
            ),
            (
                b"CONNECT api.anthropic.com HTTP/1.1\r\n\r\n",
                b"400",
                RefusalReason.MALFORMED_REQUEST,
                None,
                None,
            ),
            (
                b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n\r\nearly",
                b"400",
                RefusalReason.MALFORMED_REQUEST,
                None,
                None,
            ),
            (
                b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nX: " + b"a" * 9000 + b"\r\n\r\n",
                b"400",
                RefusalReason.MALFORMED_REQUEST,
                None,
                None,
            ),
        ]
        for request, status, reason, host, port in cases:
            with self.subTest(request=request[:40]):
                proxy = self._start()

                _, reply = self._request(proxy, request)

                self.assertIn(b" " + status + b" ", reply.split(b"\r\n")[0] + b" ")
                self.assertEqual(
                    [(r.reason, r.host, r.port, r.time) for r in proxy.refusals()],
                    [(reason, host, port, NOW)],
                )
                self.assertEqual(self.connections, [])

    def test_refuses_an_allowed_host_that_resolves_to_a_private_address(self) -> None:
        proxy = self._start(addresses=["127.0.0.1"])

        _, reply = self._request(proxy, b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n\r\n")

        self.assertTrue(reply.startswith(b"HTTP/1.1 502 "))
        self.assertEqual([r.reason for r in proxy.refusals()], [RefusalReason.UPSTREAM_NOT_PUBLIC])
        self.assertEqual(self.connections, [])

    def test_records_an_upstream_failure(self) -> None:
        def connect(address: tuple[str, int], timeout: float) -> socket.socket:
            raise ConnectionRefusedError

        proxy = EgressProxy.start(
            frozenset({"api.anthropic.com"}),
            now=lambda: NOW,
            resolve=lambda host, port: [PUBLIC_ADDRESS],
            connect=connect,
        )
        self.addCleanup(proxy.close)

        _, reply = self._request(proxy, b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n\r\n")

        self.assertTrue(reply.startswith(b"HTTP/1.1 502 "))
        self.assertEqual(
            [(f.host, f.error) for f in proxy.upstream_failures()],
            [("api.anthropic.com", "ConnectionRefusedError")],
        )
        self.assertEqual(proxy.refusals(), ())

    def test_drops_a_request_that_misses_its_deadline(self) -> None:
        proxy = self._start(request_head_deadline=timedelta(milliseconds=200))

        _, reply = self._request(proxy, b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n")

        self.assertTrue(reply.startswith(b"HTTP/1.1 400 "))
        self.assertEqual([r.reason for r in proxy.refusals()], [RefusalReason.MALFORMED_REQUEST])
        self.assertEqual(self.connections, [])

    def test_exposes_its_loopback_url(self) -> None:
        proxy = self._start()

        self.assertEqual(proxy.url, f"http://127.0.0.1:{proxy.port}")
