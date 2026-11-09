"""The wrapper's exit statuses: a contract with whoever calls it, agents included, which only
changes by addition.
"""

import enum


class ExitStatus(enum.IntEnum):
    """Where several apply, the earlier one in this order wins: refused, spend unmeasured, spend
    cap, below threshold, inconclusive.
    """

    THRESHOLD_MET = 0
    """Every case met the threshold at every level, and no run was inconclusive."""

    BELOW_THRESHOLD = 1
    """A case fell below the threshold at a level."""

    INCONCLUSIVE = 2
    """No case fell below the threshold, but some runs were inconclusive, so the results are
    incomplete.
    """

    SPEND_CAP = 3
    """The spend cap stopped the invocation before every case ran at every level. Retrying won't
    help until the budget allows.
    """

    REFUSED = 4
    """The wrapper refused to start, or to start a harness call. The summary or the error says
    why.
    """

    SPEND_UNMEASURED = 5
    """A reading of the subscription's weekly utilisation failed, so the spend can't be measured.
    If no harness call ran, retrying may help once the provider reports the utilisation again.
    Otherwise, the invocation's provisional charge blocks the subscription until the owner clears
    it.
    """

    INTERRUPTED = 130
    """The operator interrupted the invocation."""
