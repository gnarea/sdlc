import json
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sdlc_evals.code_check import Case
from sdlc_evals.harness import HarnessCall, make_harness_command
from sdlc_evals.harness_results import (
    HarnessResultUnreadable,
    collect_sandboxes,
    measure_bytes,
    read_harness_result,
    read_trace,
)
from sdlc_evals.invocation_directory import ConfinedDirectory
from sdlc_evals.levels import EffortLevel
from sdlc_evals.state.ledger import WeeklyUtilisation
from sdlc_evals.state.trust import ConfirmedTrust

CASE = Case(
    "programmer/review-implied", "programmer", 3, frozenset({"Read"}), timedelta(seconds=900)
)
OTHER = Case("architect/domain", "architect", 3, frozenset({"Read"}), timedelta(seconds=300))


class MakeHarnessCommandTest(unittest.TestCase):
    def _command(self, call: HarnessCall):  # noqa: ANN202
        directory = ConfinedDirectory(Path("/inv/calls/programmer--review-implied--low"))
        return make_harness_command(
            Path("/claude"),
            Path("/inv/plugin"),
            ConfirmedTrust(Path("/tree")),
            directory,
            call,
            "http://127.0.0.1:9",
        )

    def test_fixes_every_option_that_the_suite_depends_on(self) -> None:
        command = self._command(HarnessCall(CASE, EffortLevel.LOW, 3, 2.509))

        argv = list(command.argv)
        self.assertEqual(argv[:4], ["/claude", "plugin", "eval", "/inv/plugin"])
        for pair in (
            ["--model", "claude-opus-5-5"],
            ["--ablation", "none"],
            ["--concurrency", "1"],
            ["--max-cost-usd", "2.50"],
            ["--output-dir", "/inv/calls/programmer--review-implied--low/results"],
            ["--case", "programmer/review-implied"],
            ["--runs", "3"],
        ):
            self.assertIn(pair, [argv[index : index + 2] for index in range(len(argv) - 1)])
        for flag in ("--no-publish", "--scaffold", "--trust-plugin", "--keep-temp"):
            self.assertIn(flag, argv)
        for flag in ("--tag", "--json"):
            self.assertNotIn(flag, argv)

    def test_allows_each_of_the_calls_runs_its_time(self) -> None:
        for runs in (1, 3):
            with self.subTest(runs):
                command = self._command(HarnessCall(OTHER, EffortLevel.HIGH, runs, 5.0))

                self.assertEqual(command.argv[-2:], ("--runs", str(runs)))
                self.assertEqual(
                    command.timeout,
                    timedelta(minutes=10) + (timedelta(seconds=300) + timedelta(minutes=7)) * runs,
                )

    def test_runs_both_sessions_at_the_level_with_only_inference_leaving(self) -> None:
        environment = self._command(HarnessCall(CASE, EffortLevel.LOW, 3, 5.0)).environment

        self.assertEqual(environment["CLAUDE_CODE_EFFORT_LEVEL"], "low")
        self.assertEqual(environment["CLAUDE_CODE_SUBAGENT_EFFORT"], "low")
        self.assertEqual(environment["HTTPS_PROXY"], "http://127.0.0.1:9")
        self.assertEqual(environment["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"], "1")
        self.assertEqual(environment["HOME"], "/inv/calls/programmer--review-implied--low/home")
        self.assertFalse({"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"} & set(environment))


def trace_lines(*, delegated_effort: str | None = None) -> list[dict[str, object]]:
    return [
        {
            "type": "system",
            "subtype": "init",
            "tools": ["Task", "Read"],
            "model": "claude-opus-5-5",
        },
        {
            "type": "assistant",
            "parent_tool_use_id": None,
            "message": {
                "model": "claude-opus-5-5",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "Agent",
                        "input": {"subagent_type": "sdlc:programmer"},
                    }
                ],
            },
        },
        {
            "type": "assistant",
            "parent_tool_use_id": "t1",
            "message": {
                "model": "claude-opus-5-5",
                "content": [
                    {"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "/x"}}
                ],
            },
        },
        {
            "type": "user",
            "parent_tool_use_id": "t1",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t2",
                        "is_error": True,
                        "content": [{"type": "text", "text": "EACCES: denied"}],
                    }
                ]
            },
        },
        {
            "type": "rate_limit_event",
            "rate_limit_info": {
                "unifiedWindows": {"seven_day": {"utilization": 0.22, "resetsAt": 1794571200}}
            },
        },
        {"type": "assistant", "message": {"model": "<synthetic>", "content": "not a list"}},
        {"type": "result", "subtype": "success", "is_error": False},
    ]


class ReadTraceTest(unittest.TestCase):
    def test_extracts_what_classification_needs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / "trace.jsonl").write_text(
                "\n".join(map(json.dumps, trace_lines())) + "\nnot json\n", encoding="utf-8"
            )
            subagents = run / "projects" / "p" / "s" / "subagents"
            subagents.mkdir(parents=True)
            (subagents / "agent-1.jsonl").write_text(
                json.dumps({"type": "assistant", "effort": "low"}) + "\n", encoding="utf-8"
            )
            (run / "projects" / "p" / "s.jsonl").write_text(
                json.dumps({"type": "assistant", "message": {"effort": "low"}}) + "\n",
                encoding="utf-8",
            )

            trace = read_trace(run)

        self.assertEqual(trace.offered_tools, frozenset({"Task", "Read"}))
        self.assertEqual(
            [(call.name, call.is_delegated) for call in trace.tool_calls],
            [("Agent", False), ("Read", True)],
        )
        self.assertEqual(trace.error_tool_results, ("EACCES: denied",))
        self.assertEqual(trace.result_subtype, "success")
        self.assertFalse(trace.is_api_error)
        self.assertEqual(
            (trace.main_models, trace.delegated_models),
            (frozenset({"claude-opus-5-5"}), frozenset({"claude-opus-5-5"})),
        )
        self.assertEqual(
            (trace.main_session_efforts, trace.delegated_session_efforts),
            (frozenset({"low"}), frozenset({"low"})),
        )
        self.assertEqual(
            trace.utilisations, (WeeklyUtilisation(0.22, datetime.fromtimestamp(1794571200, UTC)),)
        )

    def test_leaves_out_utilisation_that_is_malformed(self) -> None:
        def event(utilization: object, resets_at: object) -> dict[str, object]:
            window = {"utilization": utilization, "resetsAt": resets_at}
            return {
                "type": "rate_limit_event",
                "rate_limit_info": {"unifiedWindows": {"seven_day": window}},
            }

        lines = [
            event(True, 1794571200),
            event(-0.1, 1794571200),
            event(0.3, True),
            event(0.3, "1794571200"),
            event(0.3, 10**20),
            event(0.3, 1794571200),
        ]
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / "trace.jsonl").write_text(
                "\n".join(map(json.dumps, lines))
                + '\n{"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": '
                '{"seven_day": {"utilization": Infinity, "resetsAt": 1794571200}}}}\n',
                encoding="utf-8",
            )

            trace = read_trace(run)

        self.assertEqual(
            trace.utilisations, (WeeklyUtilisation(0.3, datetime.fromtimestamp(1794571200, UTC)),)
        )

    def test_reads_nothing_from_a_missing_trace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            trace = read_trace(Path(directory))

        self.assertEqual(
            (trace.offered_tools, trace.tool_calls, trace.result_subtype), (frozenset(), (), None)
        )


class HarnessResultTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.call_directory = ConfinedDirectory(Path(temporary.name) / "call")
        self.call_directory.make()

    def _sandbox(self, name: str) -> Path:
        sandbox = self.call_directory.tmp / name
        (sandbox / "out").mkdir(parents=True)
        (sandbox / "out" / "trace.jsonl").write_text('{"type": "result"}\n', encoding="utf-8")
        (sandbox / "config" / "projects" / "p").mkdir(parents=True)
        (sandbox / "config" / "projects" / "p" / "s.jsonl").write_text("{}\n", encoding="utf-8")
        (sandbox / "sealed" / "home").mkdir(parents=True)
        (sandbox / "sealed" / "home" / "x").write_text("x", encoding="utf-8")
        os.chmod(sandbox / "sealed", 0)
        os.chmod(sandbox, 0o500)
        return sandbox

    def _write_result(self, trace_path: str) -> None:
        run = {
            "score": 1,
            "passed": True,
            "costUsd": 0.5,
            "error": None,
            "tracePath": trace_path,
            "startedAt": "t",
            "graders": [{"name": "delegated", "passed": True, "explanation": "ok"}],
        }
        document = {
            "claudeVersion": "2.1.317",
            "costUsd": 0.5,
            "cases": [{"name": "programmer/review-implied", "arms": {"with": [run]}}],
        }
        (self.call_directory.results / "aggregate-result.json").write_text(
            json.dumps(document), encoding="utf-8"
        )

    def test_reads_each_run_and_copies_its_records_before_deleting_its_sealed_sandbox(self) -> None:
        sandbox = self._sandbox("claude-eval-abc")
        stray = self._sandbox("claude-eval-def")
        self._write_result(str(sandbox / "out" / "trace.jsonl"))
        traces = self.call_directory.path.parent / "traces"

        result = read_harness_result(self.call_directory)
        space = measure_bytes(self.call_directory.tmp)
        copies = collect_sandboxes(self.call_directory, result, traces)

        self.assertEqual(
            [(run.case, run.index, run.passed, run.cost_usd) for run in result.runs],
            [("programmer/review-implied", 1, True, 0.5)],
        )
        self.assertLess(0, space)
        copy = traces / "programmer--review-implied" / "run-1"
        self.assertEqual(copies, {("programmer/review-implied", 1): copy})
        self.assertTrue((copy / "trace.jsonl").is_file())
        self.assertTrue((copy / "projects" / "p" / "s.jsonl").is_file())
        self.assertTrue((traces / "unclaimed" / stray.name / "trace.jsonl").is_file())
        self.assertEqual(list(self.call_directory.tmp.iterdir()), [])

    def test_refuses_a_trace_path_outside_the_call(self) -> None:
        self._sandbox("claude-eval-abc")
        self._write_result("/home/operator/.ssh/out/trace.jsonl")

        copies = collect_sandboxes(
            self.call_directory,
            read_harness_result(self.call_directory),
            self.call_directory.path.parent / "traces",
        )

        self.assertEqual(copies, {})

    def test_reports_an_unreadable_result(self) -> None:
        with self.assertRaises(HarnessResultUnreadable):
            read_harness_result(self.call_directory)
        (self.call_directory.results / "aggregate-result.json").write_text(
            '{"cases": "x"}', encoding="utf-8"
        )
        with self.assertRaises(HarnessResultUnreadable):
            read_harness_result(self.call_directory)
