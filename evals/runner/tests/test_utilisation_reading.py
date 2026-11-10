import io
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sdlc_evals.confinement import ConfinedResult, Policy
from sdlc_evals.harness_call import CallContext
from sdlc_evals.invocation_directory import InvocationDirectory
from sdlc_evals.state.ledger import WeeklyUtilisation
from sdlc_evals.state.trust import ConfirmedTrust
from sdlc_evals.utilisation_reading import take_reading

NOW = datetime(2026, 11, 9, 12, tzinfo=UTC)


class _Confinement:
    """Runs the reading as Claude Code would, writing the scripted lines where its output goes."""

    def __init__(self, lines: list[dict[str, object]], is_timed_out: bool = False) -> None:
        self._lines = lines
        self._is_timed_out = is_timed_out
        self.runs: list[tuple[Policy, list[str], timedelta, Path | None]] = []

    def run(
        self,
        policy: Policy,
        argv: list[str],
        timeout: timedelta,
        output_log: Path | None = None,
    ) -> ConfinedResult:
        self.runs.append((policy, argv, timeout, output_log))
        assert output_log is not None
        output_log.write_text("\n".join(map(json.dumps, self._lines)) + "\n", encoding="utf-8")
        exit_code = None if self._is_timed_out else 0
        return ConfinedResult(exit_code, self._is_timed_out, "", "")


def rate_limit_event(utilization: float, resets_at: datetime) -> dict[str, object]:
    window = {"utilization": utilization, "resetsAt": int(resets_at.timestamp())}
    return {
        "type": "rate_limit_event",
        "rate_limit_info": {"unifiedWindows": {"seven_day": window}},
    }


class TakeReadingTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = InvocationDirectory(Path(temporary.name))
        self.progress = io.StringIO()

    def _take(self, confinement: _Confinement) -> WeeklyUtilisation | None:
        context = CallContext(
            confinement=confinement,  # type: ignore[arg-type]
            claude=Path("/claude"),
            plugin=Path("/inv/plugin"),
            trust=ConfirmedTrust(Path("/tree")),
            directory=self.directory,
            proxy_url="http://127.0.0.1:9",
            make_policy=lambda writable, environment: Policy(
                readable_directories=(),
                writable_directory=writable,
                proxy_port=9,
                denied_paths=(),
                environment=environment,
                inherited_variables=("CLAUDE_CODE_OAUTH_TOKEN",),
            ),
            progress=self.progress,
        )
        return take_reading(context, 2, lambda: NOW)

    def test_reads_the_last_utilisation_that_the_response_reported(self) -> None:
        reset = NOW + timedelta(days=4)
        confinement = _Confinement(
            [{"type": "system"}, rate_limit_event(0.29, reset), rate_limit_event(0.3, reset)]
        )

        reading = self._take(confinement)

        self.assertEqual(reading, WeeklyUtilisation(0.3, reset))
        ((policy, argv, timeout, output_log),) = confinement.runs
        reading_directory = self.directory.path / "readings" / "reading-2"
        self.assertEqual(policy.writable_directory, reading_directory)
        self.assertEqual(
            policy.environment["CLAUDE_CONFIG_DIR"], str(reading_directory / "config")
        )
        self.assertNotIn("CLAUDE_CODE_EFFORT_LEVEL", policy.environment)
        self.assertEqual(
            argv,
            [
                "/claude",
                "--print",
                "--output-format",
                "stream-json",
                "--verbose",
                "--model",
                "haiku",
                "--tools",
                "",
                "--no-session-persistence",
                "Reply with OK.",
            ],
        )
        self.assertEqual(timeout, timedelta(minutes=5))
        self.assertEqual(output_log, reading_directory / "results" / "trace.jsonl")
        self.assertEqual(self.progress.getvalue(), "")

    def test_says_why_it_has_no_plausible_reading(self) -> None:
        cases = [
            ("none reported", _Confinement([{"type": "result"}]), "the response reported none"),
            (
                "timed out",
                _Confinement([], is_timed_out=True),
                "the response reported none (timed out)",
            ),
            (
                "a week that already reset",
                _Confinement([rate_limit_event(0.3, NOW)]),
                "the week must reset within 7 days, 1:00:00",
            ),
            (
                "a week too far ahead",
                _Confinement([rate_limit_event(0.3, NOW + timedelta(days=7, hours=2))]),
                "the week must reset within 7 days, 1:00:00",
            ),
        ]
        for label, confinement, expected in cases:
            with self.subTest(label):
                self.setUp()

                reading = self._take(confinement)

                self.assertIsNone(reading)
                self.assertIn(
                    f"Couldn't read the weekly utilisation: {expected}", self.progress.getvalue()
                )

    def test_accepts_a_week_that_resets_at_the_furthest_plausible_time(self) -> None:
        reset = NOW + timedelta(days=7, hours=1)

        self.assertEqual(
            self._take(_Confinement([rate_limit_event(0.3, reset)])),
            WeeklyUtilisation(0.3, reset),
        )
