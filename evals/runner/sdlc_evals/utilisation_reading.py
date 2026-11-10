"""The wrapper's own reading of the subscription's weekly utilisation: the smallest model request
that reports it, made by the pinned Claude Code under the same confinement and credential as the
harness.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from .harness import ConfinedCommand, make_environment
from .harness_call import CallContext
from .harness_results import read_trace
from .invocation_directory import ConfinedDirectory
from .state.ledger import WeeklyUtilisation
from .terminal_status import end_status

READING_MODEL = "haiku"
READING_PROMPT = "Reply with OK."
READING_OUTPUT_FILE = "trace.jsonl"
# Long enough for Claude Code to retry a failed request a few times, since a failed reading stops
# the invocation, and leaves its provisional charge to block the subscription.
READING_TIMEOUT = timedelta(minutes=5)
# The weekly window resets within seven days of any reading. The hour allows for the provider's
# clock and the operator's to differ.
MAX_WEEK_AHEAD = timedelta(days=7, hours=1)


def make_reading_command(
    claude: Path, directory: ConfinedDirectory, proxy_url: str
) -> ConfinedCommand:
    """Build the command for a single request without any tool, which carries as little as
    Claude Code allows.
    """
    argv = (
        str(claude),
        "--print",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        READING_MODEL,
        "--tools",
        "",
        "--no-session-persistence",
        READING_PROMPT,
    )
    return ConfinedCommand(argv, make_environment(directory, proxy_url), READING_TIMEOUT)


def take_reading(
    context: CallContext, index: int, now: Callable[[], datetime]
) -> WeeklyUtilisation | None:
    """Read the weekly utilisation, or say why it couldn't be read and return None."""
    directory = context.directory.reading(index)
    directory.make()
    command = make_reading_command(context.claude, directory, context.proxy_url)
    policy = context.make_policy(directory.path, command.environment)
    output = directory.results / READING_OUTPUT_FILE
    confined = context.confinement.run(
        policy, list(command.argv), command.timeout, output_log=output
    )
    readings = read_trace(directory.results).utilisations
    reading = readings[-1] if readings else None
    taken_at = now()
    if reading is not None and taken_at < reading.resets_at <= taken_at + MAX_WEEK_AHEAD:
        return reading
    if reading is None:
        problem = "the response reported none"
    else:
        problem = f"the week must reset within {MAX_WEEK_AHEAD} (got {reading.resets_at})"
    ending = "timed out" if confined.is_timed_out else f"exit status {confined.exit_code}"
    end_status(context.progress)
    context.progress.write(
        f"Couldn't read the weekly utilisation: {problem} ({ending}). See {output}\n"
    )
    return None
