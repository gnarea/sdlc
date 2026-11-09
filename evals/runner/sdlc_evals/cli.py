"""The wrapper's command line, which wires the operator's choices to the invocation and does nothing
else.
"""

import argparse
import os
import pwd
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from .controlling_terminal import open_controlling_terminal
from .exit_status import ExitStatus
from .invocation import InvocationOptions, Operator, run_invocation, self_test_only
from .levels import EffortLevel
from .spend import ApiKeyChoice, SubscriptionChoice
from .state.ledger import clear_provisional_charge, find_provisional_charges
from .state.store import InvocationLockHeld, StateStore, StateStoreUnusable
from .state.subscription_token import InvalidToken, read_token_input, store_token

MAX_RUNS_PER_CASE = 3


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(ExitStatus.REFUSED, f"{self.prog}: error: {message}\n")


def main() -> int:
    command, options = parse_command(sys.argv[1:])
    operator = Operator(
        environment=dict(os.environ),
        account_home=Path(pwd.getpwuid(os.getuid()).pw_dir),
        now=lambda: datetime.now(UTC),
        open_terminal=open_controlling_terminal,
        progress=sys.stderr,
    )
    try:
        match command:
            case "run":
                assert options is not None
                return run_invocation(options, operator)
            case "self-test":
                return self_test_only(operator)
            case "store-token":
                return _store_token(operator)
            case "clear-charge":
                return _clear_charge(operator)
    except KeyboardInterrupt:
        return ExitStatus.INTERRUPTED
    raise AssertionError(f"Unknown command {command!r}")


def parse_command(argv: Sequence[str]) -> tuple[str, InvocationOptions | None]:
    """Parse the command line, exiting with the refusal status if it's invalid. Only `run` takes
    options.
    """
    arguments = _make_parser().parse_args(argv)
    if arguments.command == "run":
        return arguments.command, _make_options(arguments)
    return arguments.command, None


def _make_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="evals/runner", description="Run the agent eval suite, confined, within budget."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run the suite (all agents and levels by default)")
    run.add_argument(
        "--agent", action="append", dest="agents", help="an agent to test (repeatable)"
    )
    run.add_argument(
        "--level",
        action="append",
        dest="levels",
        choices=[level.value for level in EffortLevel],
        help="an effort level (repeatable)",
    )
    run.add_argument("--case", dest="case_name", help="a single case, named (agent)/(case)")
    run.add_argument(
        "--runs",
        dest="runs_per_case",
        type=int,
        choices=range(1, MAX_RUNS_PER_CASE + 1),
        help="runs per case and level, instead of each case's own",
    )
    run.add_argument(
        "--credential",
        choices=["subscription", "api-key"],
        default="subscription",
        help="where the credential comes from",
    )
    run.add_argument(
        "--max-cost-usd",
        type=float,
        help="the invocation's cap in dollars, required with --credential api-key",
    )
    commands.add_parser("self-test", help="check the confinement, without any model call")
    commands.add_parser(
        "store-token", help="store the token from `claude setup-token`, read without echo"
    )
    commands.add_parser(
        "clear-charge",
        help="clear a provisional charge that blocks the subscription, asked in person",
    )
    return parser


def _make_options(arguments: argparse.Namespace) -> InvocationOptions:
    if arguments.credential == "api-key":
        if arguments.max_cost_usd is None or arguments.max_cost_usd <= 0:
            _make_parser().error("--credential api-key needs a positive --max-cost-usd")
        credential: SubscriptionChoice | ApiKeyChoice = ApiKeyChoice(arguments.max_cost_usd)
    elif arguments.max_cost_usd is not None:
        _make_parser().error(
            "--max-cost-usd only applies to --credential api-key; the subscription's cap comes from its budget"
        )
    else:
        credential = SubscriptionChoice()
    levels = (
        tuple(EffortLevel(level) for level in arguments.levels)
        if arguments.levels
        else tuple(EffortLevel)
    )
    return InvocationOptions(
        agents=tuple(arguments.agents) if arguments.agents else None,
        levels=tuple(dict.fromkeys(levels)),
        case_name=arguments.case_name,
        runs_per_case=arguments.runs_per_case,
        credential=credential,
    )


def _store_token(operator: Operator) -> int:
    try:
        store = StateStore.init(operator.account_home)
        token_input = read_token_input(sys.stdin.buffer, operator.progress)
        stored = store_token(store, token_input, operator.now())
    except (StateStoreUnusable, InvalidToken) as error:
        operator.progress.write(f"{error}\n")
        return ExitStatus.REFUSED
    operator.progress.write(
        f"Stored the subscription token in {store.directory}; it expires around {stored.expires_at():%Y-%m-%d}.\n"
    )
    return ExitStatus.THRESHOLD_MET


def _clear_charge(operator: Operator) -> int:
    holder = f"pid {os.getpid()}, clearing a provisional charge, since {operator.now().isoformat()}"
    try:
        store = StateStore.init(operator.account_home)
        with store.lock_invocation(holder):
            charges = find_provisional_charges(store, operator.now())
            cleared = [
                charge.invocation_id
                for charge in charges
                if clear_provisional_charge(store, charge, operator.now(), operator.open_terminal)
            ]
    except (StateStoreUnusable, InvocationLockHeld) as error:
        operator.progress.write(f"{error}\n")
        return ExitStatus.REFUSED
    if not charges:
        operator.progress.write("No provisional charge blocks the subscription.\n")
        return ExitStatus.THRESHOLD_MET
    if len(cleared) < len(charges):
        operator.progress.write("A provisional charge still blocks the subscription.\n")
        return ExitStatus.REFUSED
    operator.progress.write(f"Cleared the provisional charge of {', '.join(cleared)}.\n")
    return ExitStatus.THRESHOLD_MET
