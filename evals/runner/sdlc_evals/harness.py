"""The confined harness's command line and environment for one harness call: one case at one
level.

The wrapper passes no other options through, so widening what a run can do takes a reviewed change
here.
"""

import math
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .code_check import Case, Suite
from .invocation_directory import ConfinedDirectory
from .levels import EffortLevel
from .state.trust import ConfirmedTrust

MODEL = "claude-opus-5-5"
# Pinned so that every invocation records the same judge. In the pilot, the harness's default (Haiku)
# failed a run that plainly met its criterion, so the judge is Sonnet.
JUDGE_MODEL = "claude-sonnet-5-5"
GATED_TOOLS_GRANTED = ("Write", "Edit")
# The harness kills a scaffold step after two minutes, and makes three judge calls per LLM grader.
SCAFFOLD_ALLOWANCE = timedelta(minutes=2)
GRADING_ALLOWANCE = timedelta(minutes=5)
CALL_OVERHEAD = timedelta(minutes=10)


class InvalidSelection(Exception):
    """The operator chose an agent or a case that the suite lacks, or agents without cases.
    Retrying won't help: choose among the suite's agents and their cases.
    """


@dataclass(frozen=True)
class CaseSelection:
    """Which cases an invocation runs, in the suite's order, and how many times."""

    cases: tuple[Case, ...]
    agents: tuple[str, ...]
    runs_per_case: int | None

    @classmethod
    def make(
        cls,
        suite: Suite,
        agents: tuple[str, ...] | None,
        case_names: frozenset[str] | None,
        runs_per_case: int | None,
    ) -> CaseSelection:
        """Select the cases of the agents named, or of every agent, and only those named, if any."""
        chosen_agents = agents or suite.agents
        unknown_agents = sorted(set(chosen_agents) - set(suite.agents))
        if unknown_agents:
            raise InvalidSelection(
                f"Agents must be among {list(suite.agents)} (got {unknown_agents})"
            )
        cases = tuple(case for case in suite.cases if case.agent in chosen_agents)
        if case_names is not None:
            unknown_cases = sorted(case_names - {case.name for case in cases})
            if unknown_cases:
                raise InvalidSelection(
                    f"Cases must be among those of the chosen agents (got {unknown_cases})"
                )
            cases = tuple(case for case in cases if case.name in case_names)
        if not cases:
            raise InvalidSelection("The chosen agents have no cases")
        return cls(cases=cases, agents=tuple(chosen_agents), runs_per_case=runs_per_case)

    def runs_of(self, case: Case) -> int:
        return self.runs_per_case or case.runs


@dataclass(frozen=True)
class HarnessCall:
    """One case at one level, run so many times, within a dollar cap."""

    case: Case
    level: EffortLevel
    runs: int
    cap_usd: float


@dataclass(frozen=True)
class ConfinedCommand:
    argv: tuple[str, ...]
    environment: dict[str, str]
    timeout: timedelta


def make_harness_command(
    claude: Path,
    plugin: Path,
    trust: ConfirmedTrust,
    directory: ConfinedDirectory,
    call: HarnessCall,
    proxy_url: str,
) -> ConfinedCommand:
    """Build the command for a harness call on the snapshot of the plugin, whose worktree the
    operator trusts.
    """
    del trust
    argv = [
        str(claude),
        "plugin",
        "eval",
        str(plugin),
        "--model",
        MODEL,
        "--judge-model",
        JUDGE_MODEL,
        "--ablation",
        "none",
        "--no-publish",
        "--concurrency",
        "1",
        "--scaffold",
        "--trust-plugin",
        "--keep-temp",
        "--max-cost-usd",
        # Rounding down to whole cents keeps the harness's cap within the call's.
        f"{math.floor(call.cap_usd * 100) / 100:.2f}",
        "--output-dir",
        str(directory.results),
    ]
    for tool in GATED_TOOLS_GRANTED:
        argv += ["--allow-tools", tool]
    # The harness matches the whole name, and case names hold no glob characters, so this selects
    # the one case.
    argv += ["--case", call.case.name, "--runs", str(call.runs)]
    environment = {
        **make_environment(directory, proxy_url),
        "CLAUDE_CODE_EFFORT_LEVEL": call.level.value,
        "CLAUDE_CODE_SUBAGENT_EFFORT": call.level.value,
    }
    return ConfinedCommand(
        argv=tuple(argv), environment=environment, timeout=_estimate_timeout(call)
    )


def make_environment(directory: ConfinedDirectory, proxy_url: str) -> dict[str, str]:
    """The environment of a confined Claude Code process, whose own files stay in its directory,
    and whose only traffic is inference through the proxy.
    """
    return {
        "HOME": str(directory.home),
        "CLAUDE_CONFIG_DIR": str(directory.config),
        "TMPDIR": str(directory.tmp),
        "XDG_CONFIG_HOME": str(directory.home / ".config"),
        "XDG_CACHE_HOME": str(directory.home / ".cache"),
        "XDG_DATA_HOME": str(directory.home / ".local" / "share"),
        "XDG_STATE_HOME": str(directory.home / ".local" / "state"),
        "LANG": "C.UTF-8",
        "TERM": "dumb",
        "NO_COLOR": "1",
        "HTTPS_PROXY": proxy_url,
        "https_proxy": proxy_url,
        "HTTP_PROXY": proxy_url,
        "http_proxy": proxy_url,
        # The harness switches non-essential traffic off for every run, so runs can't fetch
        # remote feature flags. It's switched off for the harness and the readings too, so that
        # nothing but inference leaves the machine.
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_TELEMETRY": "1",
        "DISABLE_ERROR_REPORTING": "1",
        "DISABLE_AUTOUPDATER": "1",
    }


def _estimate_timeout(call: HarnessCall) -> timedelta:
    per_run = call.case.timeout + SCAFFOLD_ALLOWANCE + GRADING_ALLOWANCE
    return per_run * call.runs + CALL_OVERHEAD
