"""Kernel-enforced confinement through the nono binary, which every process it starts inherits.

nono's Python library can't confine this suite on Linux: it applies no pathname AF_UNIX mediation,
so a
confined process could connect to the operator's D-Bus session bus, and its `sandboxed_exec`
captures
output instead of streaming it. The nono binary does both.
"""

import contextlib
import hashlib
import json
import platform
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import IO

from .process_tree import kill_stragglers, stop_tree

NONO_VERSION = "0.81.0"
# SHA-256 of the `nono` binary in the release's tarballs for Linux, which fix every advisory
# published before it.
NONO_SHA256_BY_MACHINE = {
    "aarch64": "6d9c53bed08eb81e5b4c38fdf1d0089087566dc9035da7614ce26d011ed2e8f4",
    "x86_64": "d8ac3fa92d87bfbe80a52ea68729a8b5b461149437d55225c356b82af5bfc90f",
}
TERMINATION_GRACE = timedelta(seconds=30)

# System paths that the pinned Claude Code, bash, cp, and git need, none of which holds the
# operator's data.
SYSTEM_READABLE_DIRECTORIES = ("/usr", "/etc/ssl", "/etc/ca-certificates")
SYSTEM_READABLE_FILES = (
    "/etc/ld.so.cache",
    "/etc/passwd",
    "/etc/group",
    "/etc/nsswitch.conf",
    "/etc/hosts",
    "/etc/localtime",
    "/etc/os-release",
    "/dev/urandom",
    "/dev/random",
)
SYSTEM_WRITABLE_FILES = ("/dev/null",)
# nono adds these groups to every profile, and they would grant reading most of the system and
# writing /tmp.
NONO_DEFAULT_GROUPS = (
    "system_read_macos",
    "system_read_linux_core",
    "system_write_macos",
    "system_write_linux",
    "user_tools",
    "homebrew_macos",
    "homebrew_linux",
    "dangerous_commands",
    "dangerous_commands_macos",
    "dangerous_commands_linux",
)


class NonoUnavailable(Exception):
    """The pinned nono binary isn't installed where the wrapper looks. Retrying won't help until it
    is.
    """


@dataclass(frozen=True)
class NonoBinary:
    path: Path

    @classmethod
    def locate(cls, search_path: str) -> NonoBinary:
        """Find `nono` on the search path, and refuse it unless it's the pinned release's binary."""
        expected_sha256 = NONO_SHA256_BY_MACHINE.get(platform.machine())
        if expected_sha256 is None:
            raise NonoUnavailable(
                f"The suite only supports Linux on {sorted(NONO_SHA256_BY_MACHINE)} (got {platform.machine()})"
            )
        found = shutil.which("nono", path=search_path)
        if found is None:
            raise NonoUnavailable(f"nono {NONO_VERSION} must be on PATH")
        path = Path(found).resolve()
        with path.open("rb") as binary:
            actual_sha256 = hashlib.file_digest(binary, "sha256").hexdigest()
        if actual_sha256 != expected_sha256:
            raise NonoUnavailable(
                f"{path} must be the nono {NONO_VERSION} release binary (SHA-256 {expected_sha256}, got {actual_sha256})"
            )
        return cls(path)


@dataclass(frozen=True)
class Policy:
    """What a confined process tree may reach. Everything else is denied."""

    readable_directories: tuple[Path, ...]
    writable_directory: Path
    proxy_port: int
    denied_paths: tuple[Path, ...]
    environment: Mapping[str, str]
    inherited_variables: tuple[str, ...] = ()

    def render(self) -> dict[str, object]:
        """Render the policy as a nono profile, which holds no secret."""
        for name, value in self.environment.items():
            if "$" in value:
                raise ValueError(
                    f"Confined environment values must not need expansion (got {name})"
                )
        return {
            "meta": {"name": "sdlc-evals"},
            "groups": {"include": [], "exclude": list(NONO_DEFAULT_GROUPS)},
            "workdir": {"access": "none"},
            "filesystem": {
                "read": [*SYSTEM_READABLE_DIRECTORIES, *map(str, self.readable_directories)],
                "read_file": list(SYSTEM_READABLE_FILES),
                "allow": [str(self.writable_directory)],
                "allow_file": list(SYSTEM_WRITABLE_FILES),
                "deny": [str(path) for path in self.denied_paths],
            },
            "network": {"block": True, "connect_port": [self.proxy_port]},
            "linux": {"af_unix_mediation": "pathname", "sandbox_policy": "auto"},
            "security": {
                "signal_mode": "allow_same_sandbox",
                "process_info_mode": "isolated",
                "ipc_mode": "shared_memory_only",
                "capability_elevation": False,
            },
            "open_urls": {"allow_origins": [], "allow_localhost": False},
            # An empty allowlist would pass every variable through, so it always names one.
            "environment": {
                "allow_vars": ["LANG", *self.inherited_variables],
                "set_vars": dict(self.environment),
            },
        }


@dataclass(frozen=True)
class Confinement:
    """Runs commands under a policy, with nono's own state kept where no confined process can reach
    it.
    """

    nono: NonoBinary
    state_directory: Path
    search_path: str
    inherited_environment: Mapping[str, str] = field(default_factory=dict, repr=False)

    def run(
        self,
        policy: Policy,
        command: list[str],
        timeout: timedelta,
        *,
        is_output_captured: bool = False,
        output_log: Path | None = None,
    ) -> ConfinedResult:
        """Run the command under the policy. Its output is captured, written to `output_log`, or
        else passed through to the terminal.
        """
        profile_path = self._write_profile(policy)
        environment = self._nono_environment()
        for name in policy.inherited_variables:
            environment[name] = self.inherited_environment[name]
        argv = [
            str(self.nono.path),
            "run",
            "--silent",
            "--no-audit",
            "--no-rollback",
            "--profile",
            str(profile_path),
            "--",
            *command,
        ]
        with contextlib.ExitStack() as stack:
            output: int | IO[bytes] | None = subprocess.PIPE if is_output_captured else None
            if output_log is not None:
                output = stack.enter_context(output_log.open("wb"))
            process = subprocess.Popen(
                argv,
                env=environment,
                cwd=policy.writable_directory,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT if output_log is not None else output,
            )
        try:
            stdout, stderr = process.communicate(timeout=timeout.total_seconds())
            is_timed_out = False
        except subprocess.TimeoutExpired:
            stop_tree(process, TERMINATION_GRACE)
            stdout, stderr = process.communicate()
            is_timed_out = True
        except KeyboardInterrupt:
            stop_tree(process, TERMINATION_GRACE)
            raise
        # Nothing that the confined tree started may outlive it, and overlap the next harness call.
        kill_stragglers()
        return ConfinedResult(
            exit_code=process.returncode,
            is_timed_out=is_timed_out,
            stdout=(stdout or b"").decode("utf-8", "replace"),
            stderr=(stderr or b"").decode("utf-8", "replace"),
        )

    def _write_profile(self, policy: Policy) -> Path:
        profiles = self.state_directory / "profiles"
        profiles.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = profiles / f"{policy.writable_directory.name}.json"
        path.write_text(json.dumps(policy.render(), indent=2), encoding="utf-8")
        return path

    def _nono_environment(self) -> dict[str, str]:
        home = self.state_directory / "home"
        directories = {
            "HOME": home,
            "TMPDIR": self.state_directory / "tmp",
            "XDG_CONFIG_HOME": home / ".config",
            "XDG_STATE_HOME": home / ".local" / "state",
            "XDG_DATA_HOME": home / ".local" / "share",
            "XDG_CACHE_HOME": home / ".cache",
        }
        for directory in directories.values():
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        return {
            "PATH": self.search_path,
            "LANG": "C.UTF-8",
            **{name: str(path) for name, path in directories.items()},
        }


@dataclass(frozen=True)
class ConfinedResult:
    exit_code: int
    is_timed_out: bool
    stdout: str
    stderr: str
