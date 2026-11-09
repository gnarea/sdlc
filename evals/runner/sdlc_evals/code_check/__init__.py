"""The code check: what the working tree would run, refused unless an allowlist names its kind."""

from pathlib import Path

from .model import Case, Finding, Refused, Suite
from .plugin import check_plugin, check_root
from .suite import check_suite

__all__ = ["Case", "Finding", "Refused", "Suite", "check_plugin_snapshot"]


def check_plugin_snapshot(worktree: Path, snapshot: Path) -> Suite | Refused:
    """Vouch for the snapshot of the plugin and its cases, and for the working tree's root, or
    refuse them with every finding.
    """
    findings = check_root(worktree)
    agents, plugin_findings = check_plugin(snapshot)
    cases, suite_findings = check_suite(snapshot, agents)
    findings += plugin_findings + suite_findings
    if findings:
        return Refused(tuple(findings))
    return Suite(agents=agents, cases=cases)
