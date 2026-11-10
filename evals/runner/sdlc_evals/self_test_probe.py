"""The confinement self-test's probe, which runs inside the confinement, two levels below its root.

It runs on the system's Python with the standard library only, imports nothing from the wrapper,
makes no
request to any model, and prints one JSON object per check.
"""

import errno
import json
import os
import socket
import ssl
import subprocess
import sys
from collections.abc import Callable

DENIED_ERRNOS = frozenset({errno.EACCES, errno.EPERM})
NETWORK_TIMEOUT_SECONDS = 10
COMMAND_TIMEOUT_SECONDS = 30
MAX_PROXY_REPLY_BYTES = 4096


def main() -> None:
    spec = json.loads(sys.argv[1])
    for path in spec["denied_reads"]:
        _report(f"read {path}", "denied", lambda path=path: _read(path))
    for directory in spec["denied_writes"]:
        _report(
            f"write in {directory}",
            "denied",
            lambda directory=directory: _write(directory, spec["marker"]),
        )
    _report(
        "write in the writable directory",
        "allowed",
        lambda: _write(spec["writable_directory"], spec["marker"]),
    )
    _report("UDP over IPv4", "denied", lambda: _udp(socket.AF_INET))
    _report("UDP over IPv6", "denied", lambda: _udp(socket.AF_INET6))
    _report(f"TCP to port {spec['other_port']}", "denied", lambda: _tcp(spec["other_port"]))
    _report(
        f"proxy to {spec['refused_host']}",
        "denied",
        lambda: _proxy(spec["proxy_port"], spec["refused_host"]),
    )
    _report(
        f"proxy to {spec['allowed_host']}",
        "allowed",
        lambda: _proxy_tls(spec["proxy_port"], spec["allowed_host"]),
    )
    for path in spec["unix_sockets"]:
        _report(f"Unix socket {path}", "denied", lambda path=path: _unix(path))
    _report("abstract Unix socket", "denied", lambda: _unix("\0" + spec["abstract_socket"]))
    _report(
        "fixture-copying step",
        "allowed",
        lambda: _scaffold(spec["scaffold_script"], spec["workspace"]),
    )
    _report(
        "search tool",
        "allowed",
        lambda: _ripgrep(spec["claude"], spec["writable_directory"], spec["marker"]),
    )
    _report(
        "pinned Claude Code",
        "allowed",
        lambda: _claude_version(spec["claude"], spec["claude_version"]),
    )


def _report(check: str, expectation: str, attempt: Callable[[], None]) -> None:
    try:
        attempt()
        outcome, detail = "allowed", ""
    except OSError as error:
        is_denied = error.errno in DENIED_ERRNOS
        outcome, detail = (
            ("denied" if is_denied else "error"),
            errno.errorcode.get(error.errno or 0, str(error)),
        )
    except _ProbeError as error:
        outcome, detail = error.outcome, error.detail
    except Exception as error:  # noqa: BLE001 -- every check must report, whatever went wrong.
        outcome, detail = "error", error.__class__.__name__
    print(
        json.dumps(
            {"check": check, "expectation": expectation, "outcome": outcome, "detail": detail}
        ),
        flush=True,
    )


class _ProbeError(Exception):
    def __init__(self, outcome: str, detail: str) -> None:
        super().__init__(detail)
        self.outcome = outcome
        self.detail = detail


def _read(path: str) -> None:
    if os.path.isdir(path):
        os.listdir(path)
        return
    with open(path, "rb") as file:
        file.read(1)


def _write(directory: str, marker: str) -> None:
    path = os.path.join(directory, f".{marker}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    os.unlink(path)


def _udp(family: int) -> None:
    with socket.socket(family, socket.SOCK_DGRAM):
        pass


def _tcp(port: int) -> None:
    with socket.create_connection(("127.0.0.1", port), timeout=NETWORK_TIMEOUT_SECONDS):
        pass


def _connect_through_proxy(port: int, host: str) -> tuple[socket.socket, int]:
    connection = socket.create_connection(("127.0.0.1", port), timeout=NETWORK_TIMEOUT_SECONDS)
    connection.sendall(f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n".encode("ascii"))
    reply = b""
    while b"\r\n\r\n" not in reply and len(reply) < MAX_PROXY_REPLY_BYTES:
        chunk = connection.recv(MAX_PROXY_REPLY_BYTES)
        if not chunk:
            break
        reply += chunk
    status_line = reply.split(b"\r\n", 1)[0].decode("ascii", "replace")
    parts = status_line.split(" ")
    status = int(parts[1]) if 1 < len(parts) and parts[1].isdigit() else 0
    return connection, status


def _proxy(port: int, host: str) -> None:
    connection, status = _connect_through_proxy(port, host)
    connection.close()
    if status == 403:
        raise _ProbeError("denied", "403")
    if status != 200:
        raise _ProbeError("error", f"proxy replied {status}")


def _proxy_tls(port: int, host: str) -> None:
    """Complete a TLS handshake with the host through the proxy, and close without sending any
    request.
    """
    connection, status = _connect_through_proxy(port, host)
    if status != 200:
        connection.close()
        raise _ProbeError("denied" if status == 403 else "error", f"proxy replied {status}")
    context = ssl.create_default_context()
    with context.wrap_socket(connection, server_hostname=host):
        pass


def _unix(address: str) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(NETWORK_TIMEOUT_SECONDS)
        connection.connect(address)


def _scaffold(script: str, workspace: str) -> None:
    _run(["bash", script], cwd=workspace)
    copied = os.path.join(workspace, "copied.txt")
    if not os.path.isfile(copied):
        raise _ProbeError("error", "the fixture wasn't copied")


def _ripgrep(claude: str, directory: str, needle: str) -> None:
    corpus = os.path.join(directory, "corpus.txt")
    with open(corpus, "w", encoding="utf-8") as file:
        file.write(f"{needle}\n")
    # The harness's search tool runs the Claude Code binary as ripgrep, through its argv[0].
    output = _run(
        ["rg", "--no-config", "--files-with-matches", needle, directory], executable=claude
    )
    if corpus not in output:
        raise _ProbeError("error", "ripgrep didn't find the needle")


def _claude_version(claude: str, expected_version: str) -> None:
    output = _run([claude, "--version"])
    if not output.startswith(f"{expected_version} "):
        raise _ProbeError("error", f"unexpected version {output.strip()!r}")


def _run(command: list[str], cwd: str | None = None, executable: str | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        executable=executable,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        raise _ProbeError(
            "error",
            f"exit {completed.returncode}: {completed.stderr[-500:].decode('utf-8', 'replace')}",
        )
    return completed.stdout.decode("utf-8", "replace")


if __name__ == "__main__":
    main()
