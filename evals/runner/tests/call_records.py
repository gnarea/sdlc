from dataclasses import replace
from datetime import timedelta

from sdlc_evals.classification import Classification
from sdlc_evals.harness import ConfinedCommand, HarnessCall
from sdlc_evals.harness_call import CallRecord, RunRecord


def make_call_record(
    call: HarnessCall,
    spend_usd: float,
    classifications: tuple[Classification, ...] = (),
    **overrides: object,
) -> CallRecord:
    """A harness call that ran its runs to the given outcomes, at the given list price."""
    runs = tuple(
        RunRecord(call.case.name, index, classification, 0.5, ("claude-opus-5-5",), (), None)
        for index, classification in enumerate(classifications, start=1)
    )
    command = ConfinedCommand(
        ("claude",), {"CLAUDE_CODE_EFFORT_LEVEL": call.level.value}, timedelta(hours=1)
    )
    record = CallRecord(
        case=call.case.name,
        level=call.level,
        cap_usd=call.cap_usd,
        spend_usd=spend_usd,
        command=command,
        inherited_variables=("CLAUDE_CODE_OAUTH_TOKEN",),
        harness_exit_code=0,
        is_harness_timed_out=False,
        harness_version="2.1.317",
        harness_partial_reason=None,
        space_bytes=1024,
        unexpected_tools=frozenset(),
        runs=runs,
    )
    return replace(record, **overrides)  # type: ignore[arg-type]
