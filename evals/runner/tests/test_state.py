import errno
import io
import os
import pty
import select
import signal
import tempfile
import termios
import threading
import time
import unittest
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sdlc_evals.controlling_terminal import ask_in_person, open_controlling_terminal
from sdlc_evals.credentials import CredentialSource
from sdlc_evals.state.ledger import (
    LedgerEntry,
    WeeklyUtilisation,
    WeekReadings,
    clear_provisional_charge,
    find_provisional_charges,
    load_entries,
    record_entry,
)
from sdlc_evals.state.store import InvocationLockHeld, StateStore, StateStoreUnusable
from sdlc_evals.state.subscription_token import (
    MAX_TOKEN_INPUT_BYTES,
    InvalidToken,
    load_token,
    parse_token,
    read_token_input,
    store_token,
)
from sdlc_evals.state.trust import ConfirmedTrust, confirm_trust, is_worktree_trusted

NOW = datetime(2026, 11, 9, 12, tzinfo=UTC)
TOKEN = "sk-ant-oat01-" + "a" * 64
# Each line of the token, however it's wrapped, contains the fragment, which no prompt does.
TERMINAL_TOKEN_FRAGMENT = b"Zq3_"
TERMINAL_TOKEN = "sk-ant-oat01-" + "Zq3_Wv8-Kp" * 9 + "Zq3_W"
# How a terminal 39 columns wide pastes the token: it splits it, and sends each line break as a
# carriage return.
WRAPPED_TERMINAL_TOKEN = b"\r".join(
    TERMINAL_TOKEN[start : start + 39].encode() for start in range(0, len(TERMINAL_TOKEN), 39)
)
PROMPT_TIMEOUT_SECONDS = 5


class _Terminal(io.StringIO):
    def __init__(self, answer: str) -> None:
        super().__init__()
        self.answer = answer

    def readline(self, *_: object) -> str:
        return self.answer

    def close(self) -> None:
        pass


class _PseudoTerminal:
    """A real terminal, on whose far side the test types as the operator would once prompted."""

    def __init__(self, test: unittest.TestCase) -> None:
        self._master, slave = pty.openpty()
        self.stdin = os.fdopen(slave, "rb")
        self.progress = os.fdopen(os.dup(slave), "w", encoding="utf-8")
        self._typist: threading.Thread | None = None
        test.addCleanup(self._close)

    def type_once_prompted(
        self, keystrokes: bytes, then: Callable[[], None] = lambda: None
    ) -> None:
        def type_keystrokes() -> None:
            is_prompted = select.select([self._master], [], [], PROMPT_TIMEOUT_SECONDS)[0]
            if not is_prompted:
                # End the input, so that a read that never prompts fails rather than hangs.
                os.write(self._master, b"\x04\x04")
                return
            os.write(self._master, keystrokes)
            then()

        self._typist = threading.Thread(target=type_keystrokes)
        self._typist.start()

    def read_shown(self) -> bytes:
        """Wait for the typing to finish, then return everything that the terminal has shown."""
        assert self._typist is not None
        self._typist.join()
        shown = bytearray()
        while select.select([self._master], [], [], 0)[0]:
            shown += os.read(self._master, 4096)
        return bytes(shown)

    def is_echo_on(self) -> bool:
        return bool(termios.tcgetattr(self.stdin.fileno())[3] & termios.ECHO)

    def has_pending_input(self) -> bool:
        return bool(select.select([self.stdin], [], [], 0)[0])

    def _close(self) -> None:
        if self._typist is not None:
            self._typist.join()
        self.stdin.close()
        self.progress.close()
        os.close(self._master)


class StateStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state_home = Path(temporary.name)
        self.store = StateStore.init(self.state_home)

    def test_creates_a_private_directory_in_the_accounts_default_state_directory(self) -> None:
        self.assertEqual(self.store.directory, self.state_home / ".local" / "state" / "sdlc-evals")
        self.assertEqual(self.store.directory.stat().st_mode & 0o777, 0o700)

    def test_refuses_a_relative_home(self) -> None:
        with self.assertRaisesRegex(StateStoreUnusable, "must be absolute"):
            StateStore.init(Path("relative"))

    def test_refuses_a_directory_that_others_can_read(self) -> None:
        os.chmod(self.store.directory, 0o755)

        with self.assertRaisesRegex(StateStoreUnusable, "only accessible to"):
            StateStore.init(self.state_home)

    def test_round_trips_a_document_privately(self) -> None:
        self.store.write("x.json", 1, {"value": 42})

        self.assertEqual(self.store.read("x.json", 1), {"format_version": 1, "value": 42})
        self.assertEqual((self.store.directory / "x.json").stat().st_mode & 0o777, 0o600)
        self.assertIsNone(self.store.read("missing.json", 1))

    def test_refuses_a_document_with_another_format_version(self) -> None:
        self.store.write("x.json", 3, {})

        with self.assertRaisesRegex(StateStoreUnusable, "format version 1$"):
            self.store.read("x.json", 1)
        with self.assertRaisesRegex(StateStoreUnusable, "format version 2 or 1$"):
            self.store.read("x.json", 2, 1)

    def test_reads_a_document_with_an_older_format_version_that_the_reader_accepts(self) -> None:
        self.store.write("x.json", 1, {"value": 42})

        self.assertEqual(self.store.read("x.json", 2, 1), {"format_version": 1, "value": 42})

    def test_refuses_a_document_that_is_not_json(self) -> None:
        path = self.store.directory / "x.json"
        path.write_text("{", encoding="utf-8")
        os.chmod(path, 0o600)

        with self.assertRaisesRegex(StateStoreUnusable, "not valid JSON"):
            self.store.read("x.json", 1)

    def test_lets_one_invocation_hold_the_lock_at_a_time(self) -> None:
        lock = self.store.lock_invocation("first")

        with self.assertRaises(InvocationLockHeld) as raised:
            self.store.lock_invocation("second")
        lock.release()
        self.store.lock_invocation("third").release()

        self.assertEqual(raised.exception.holder, "first")


class TrustTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = StateStore.init(Path(temporary.name))
        self.worktree = Path(temporary.name) / "worktree"
        self.worktree.mkdir()

    def test_records_a_confirmation_given_in_person(self) -> None:
        terminal = _Terminal("yes\n")

        trust = confirm_trust(self.store, self.worktree, NOW, lambda: terminal)

        self.assertEqual(trust, ConfirmedTrust(self.worktree))
        self.assertIn(str(self.worktree), terminal.getvalue())
        self.assertTrue(terminal.getvalue().endswith("Type 'yes' to trust this worktree: "))
        self.assertTrue(is_worktree_trusted(self.store, self.worktree))

    def test_does_not_ask_again_once_confirmed(self) -> None:
        confirm_trust(self.store, self.worktree, NOW, lambda: _Terminal("yes\n"))

        def open_terminal() -> io.StringIO:
            raise AssertionError("The operator was asked again")

        self.assertEqual(
            confirm_trust(self.store, self.worktree, NOW, open_terminal),
            ConfirmedTrust(self.worktree),
        )

    def test_refuses_without_a_confirmation(self) -> None:
        def no_terminal() -> io.StringIO:
            raise OSError(errno.ENXIO, "No such device or address")

        for label, open_terminal in [
            ("declined", lambda: _Terminal("y\n")),
            ("no terminal", no_terminal),
        ]:
            with self.subTest(label):
                self.assertIsNone(confirm_trust(self.store, self.worktree, NOW, open_terminal))
                self.assertFalse(is_worktree_trusted(self.store, self.worktree))

    def test_does_not_mistake_another_error_for_a_missing_terminal(self) -> None:
        def unusable_terminal() -> io.StringIO:
            raise io.UnsupportedOperation("File or stream is not seekable.")

        with self.assertRaises(io.UnsupportedOperation):
            confirm_trust(self.store, self.worktree, NOW, unusable_terminal)
        self.assertFalse(is_worktree_trusted(self.store, self.worktree))

    def test_asks_at_a_real_controlling_terminal(self) -> None:
        for answer, expected_status in [(b"yes\n", 0), (b"y\n", 1)]:
            with self.subTest(answer):
                pid, controller = pty.fork()
                if pid == 0:
                    try:
                        trusted = ask_in_person(
                            "Trust it?", "trust this worktree", open_controlling_terminal
                        )
                    except BaseException:
                        os._exit(2)
                    os._exit(0 if trusted else 1)
                try:
                    shown = b""
                    deadline = time.monotonic() + 10
                    while b"to trust this worktree: " not in shown:
                        remaining = deadline - time.monotonic()
                        ready, _, _ = select.select([controller], [], [], max(remaining, 0))
                        if not ready:
                            break
                        try:
                            chunk = os.read(controller, 1024)
                        except OSError:
                            break
                        if not chunk:
                            break
                        shown += chunk
                    if b"to trust this worktree: " in shown:
                        os.write(controller, answer)
                    else:
                        os.kill(pid, signal.SIGKILL)
                    _, status = os.waitpid(pid, 0)
                finally:
                    os.close(controller)
                self.assertIn(b"to trust this worktree: ", shown)
                self.assertEqual(os.waitstatus_to_exitcode(status), expected_status)

    def test_forgets_worktrees_that_no_longer_exist(self) -> None:
        confirm_trust(self.store, self.worktree, NOW, lambda: _Terminal("yes\n"))
        self.worktree.rmdir()

        self.assertFalse(is_worktree_trusted(self.store, self.worktree))
        self.assertEqual(self.store.read("trust.json", 1), {"format_version": 1, "worktrees": {}})

    def test_asks_again_about_a_worktree_that_replaced_a_trusted_one(self) -> None:
        (self.worktree / ".git").write_text("gitdir: /x\n", encoding="utf-8")
        confirm_trust(self.store, self.worktree, NOW, lambda: _Terminal("yes\n"))
        (self.worktree / ".git").unlink()
        self.worktree.rmdir()
        # Filesystem timestamps advance once per clock tick, which this outlasts.
        time.sleep(0.05)
        self.worktree.mkdir()
        (self.worktree / ".git").write_text("gitdir: /x\n", encoding="utf-8")

        self.assertFalse(is_worktree_trusted(self.store, self.worktree))


class SubscriptionTokenTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = StateStore.init(Path(temporary.name))

    def test_accepts_any_plausible_token_ignoring_any_whitespace(self) -> None:
        for label, text in [
            ("surrounded", f"  {TOKEN}\n"),
            ("wrapped", f"{TOKEN[:39]}\r\n  {TOKEN[39:]}\t\u00a0\n"),
        ]:
            with self.subTest(label):
                self.assertEqual(parse_token(text), TOKEN)
        for label, text in [
            ("in another format", "xv" + "Q7_r-9" * 15),
            ("with punctuation", "tok." + "a1+/=~" * 5),
        ]:
            with self.subTest(label):
                self.assertEqual(parse_token(text), text)
        for label, invalid, expected in [
            ("empty", "", "split it over several lines"),
            ("too short", "xv" + "a" * 17, "split it over several lines"),
            ("not ASCII", "xv" + "a" * 30 + "\u00e9", "split it over several lines"),
            ("an API key", "sk-ant-api03-" + "a" * 64, "--credential api-key"),
            ("an admin key", "sk-ant-admin01-" + "a" * 64, "never an admin key"),
        ]:
            with self.subTest(label):
                with self.assertRaises(InvalidToken) as raised:
                    parse_token(invalid)
                message = str(raised.exception)
                self.assertNotIn(invalid.strip() or "\0", message)
                self.assertIn(expected, message)

    def test_keeps_the_token_until_a_year_after_it_was_stored(self) -> None:
        store_token(self.store, TOKEN, NOW)

        self.assertEqual(load_token(self.store, NOW + timedelta(days=364)).value, TOKEN)  # type: ignore[union-attr]
        self.assertIsNone(load_token(self.store, NOW + timedelta(days=365)))
        self.assertEqual(
            (self.store.directory / "subscription-token.json").stat().st_mode & 0o777, 0o600
        )

    def test_never_shows_the_token_in_its_representation(self) -> None:
        stored = store_token(self.store, TOKEN, NOW)

        self.assertNotIn(TOKEN, repr(stored))


class TokenInputTest(unittest.TestCase):
    def test_reads_a_paste_that_a_narrow_terminal_split(self) -> None:
        for label, keystrokes in [
            ("without a final line break", WRAPPED_TERMINAL_TOKEN + b"\r\r"),
            ("with a final line break", WRAPPED_TERMINAL_TOKEN + b"\r" + b"\r\r"),
            ("with the empty line above it", b"\r" + WRAPPED_TERMINAL_TOKEN + b"\r\r"),
        ]:
            with self.subTest(label):
                terminal = _PseudoTerminal(self)
                terminal.type_once_prompted(keystrokes)

                token_input = read_token_input(terminal.stdin, terminal.progress)

                shown = terminal.read_shown()
                self.assertEqual(parse_token(token_input), TERMINAL_TOKEN)
                self.assertIn(b"press Enter twice", shown)
                self.assertNotIn(TERMINAL_TOKEN_FRAGMENT, shown)
                self.assertTrue(terminal.is_echo_on())
                self.assertFalse(terminal.has_pending_input())

    def test_restores_echo_when_the_read_is_interrupted(self) -> None:
        previous_handler = signal.signal(signal.SIGINT, signal.default_int_handler)
        self.addCleanup(signal.signal, signal.SIGINT, previous_handler)
        main_thread = threading.get_ident()
        terminal = _PseudoTerminal(self)
        first_line = WRAPPED_TERMINAL_TOKEN.split(b"\r")[0]
        terminal.type_once_prompted(
            first_line + b"\r", then=lambda: signal.pthread_kill(main_thread, signal.SIGINT)
        )

        with self.assertRaises(KeyboardInterrupt):
            read_token_input(terminal.stdin, terminal.progress)

        self.assertNotIn(TERMINAL_TOKEN_FRAGMENT, terminal.read_shown())
        self.assertTrue(terminal.is_echo_on())

    def test_reads_a_piped_token_without_prompting(self) -> None:
        for label, piped in [
            ("with a final line break", f"{TOKEN}\n".encode()),
            ("split over several lines", f"{TOKEN[:39]}\r\n{TOKEN[39:]}".encode()),
            ("followed by an empty line", f"{TOKEN}\n\nNotes\n".encode()),
        ]:
            with self.subTest(label):
                progress = io.StringIO()

                token_input = read_token_input(io.BytesIO(piped), progress)

                self.assertEqual(parse_token(token_input), TOKEN)
                self.assertEqual(progress.getvalue(), "")

    def test_refuses_more_input_than_any_token_takes(self) -> None:
        at_limit = f"{TOKEN.ljust(MAX_TOKEN_INPUT_BYTES - 1)}\n".encode()

        token_input = read_token_input(io.BytesIO(at_limit), io.StringIO())
        with self.assertRaisesRegex(InvalidToken, f"exceeds {MAX_TOKEN_INPUT_BYTES} bytes"):
            read_token_input(io.BytesIO(b" " + at_limit), io.StringIO())

        self.assertEqual(len(at_limit), MAX_TOKEN_INPUT_BYTES)
        self.assertEqual(parse_token(token_input), TOKEN)


RESET = NOW + timedelta(days=1)


def subscription_entry(
    invocation_id: str = "a",
    weeks: tuple[WeekReadings, ...] = (WeekReadings(RESET, 0.29, 0.31),),
    is_provisional: bool = False,
    recorded_at: datetime = NOW,
) -> LedgerEntry:
    return LedgerEntry(
        invocation_id, CredentialSource.SUBSCRIPTION, 1.5, recorded_at, weeks, is_provisional
    )


class LedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = StateStore.init(Path(temporary.name))

    def test_keeps_entries_until_the_last_week_they_touched_resets(self) -> None:
        current = subscription_entry("current")
        straddling = subscription_entry(
            "straddling",
            (WeekReadings(NOW, 0.95, 0.97), WeekReadings(NOW + timedelta(days=7), 0.0, 0.01)),
        )
        expired = subscription_entry("expired", (WeekReadings(NOW, 0.29, 0.31),))
        provisional = subscription_entry(
            "provisional", (WeekReadings(NOW, 0.29, 0.29),), is_provisional=True
        )
        recent_api_key = LedgerEntry("recent", CredentialSource.API_KEY, 2.0, NOW, (), False)
        stale_api_key = replace(
            recent_api_key, invocation_id="stale", recorded_at=NOW - timedelta(days=7)
        )
        for entry in (current, straddling, expired, provisional, recent_api_key, stale_api_key):
            record_entry(self.store, entry, NOW - timedelta(days=8))

        self.assertEqual(
            load_entries(self.store, NOW), (current, straddling, provisional, recent_api_key)
        )
        document = self.store.read("ledger.json", 2)
        self.assertEqual(len(document["entries"]), 4)  # type: ignore[index, arg-type]

    def test_records_an_invocation_once_however_often_its_entry_is_recorded(self) -> None:
        other = subscription_entry("b")
        record_entry(self.store, other, NOW)
        first = subscription_entry("a", is_provisional=True)
        record_entry(self.store, first, NOW)
        measured = first.add_reading(WeeklyUtilisation(0.33, RESET), NOW)

        record_entry(self.store, measured, NOW)
        record_entry(self.store, measured, NOW)

        self.assertEqual(load_entries(self.store, NOW), (other, measured))

    def test_measures_each_week_by_its_first_and_last_readings(self) -> None:
        later_reset = RESET + timedelta(days=7)
        entry = LedgerEntry.make_subscription("a", WeeklyUtilisation(0.95, RESET), NOW)

        entry = replace(entry, is_provisional=True).add_spend(0.25, NOW)
        entry = entry.add_reading(WeeklyUtilisation(0.97, RESET), NOW)
        entry = entry.add_reading(WeeklyUtilisation(0.01, later_reset), NOW)
        entry = entry.add_reading(WeeklyUtilisation(0.02, later_reset), NOW)

        self.assertEqual(
            entry.weeks,
            (WeekReadings(RESET, 0.95, 0.97), WeekReadings(later_reset, 0.01, 0.02)),
        )
        self.assertEqual((entry.list_price_usd, entry.is_provisional), (0.25, False))

    def test_folds_the_per_level_format_into_an_entry_per_invocation(self) -> None:
        def level(
            invocation_id: str, usd: float, before: float | None, after: float | None
        ) -> dict[str, object]:
            def reading(fraction: float | None) -> dict[str, object] | None:
                if fraction is None:
                    return None
                return {"fraction": fraction, "resets_at": RESET.isoformat()}

            return {
                "invocation_id": invocation_id,
                "level": "low",
                "credential_source": "subscription",
                "list_price_usd": usd,
                "recorded_at": NOW.isoformat(),
                "utilisation_before": reading(before),
                "utilisation_after": reading(after),
            }

        api_key = level("api-key", 2.0, None, None) | {"credential_source": "api-key"}
        self.store.write(
            "ledger.json",
            1,
            {
                "entries": [
                    level("measured", 0.25, 0.29, 0.29),
                    level("measured", 0.5, 0.29, 0.31),
                    level("unmeasured", 5.0, None, None),
                    level("spent nothing", 0.0, None, None),
                    api_key,
                ]
            },
        )

        entries = load_entries(self.store, NOW)

        self.assertEqual(
            entries,
            (
                replace(subscription_entry("measured"), list_price_usd=0.75),
                LedgerEntry(
                    "unmeasured",
                    CredentialSource.SUBSCRIPTION,
                    5.0,
                    NOW,
                    (WeekReadings(NOW + timedelta(days=7), 0.0, 0.0),),
                    False,
                ),
                LedgerEntry("api-key", CredentialSource.API_KEY, 2.0, NOW, (), False),
            ),
        )
        document = self.store.read("ledger.json", 2)
        self.assertEqual(document["format_version"], 2)  # type: ignore[index]

    def test_refuses_a_malformed_entry(self) -> None:
        valid = {
            "invocation_id": "a",
            "credential_source": "subscription",
            "list_price_usd": 1.0,
            "recorded_at": NOW.isoformat(),
            "weeks": [
                {"resets_at": RESET.isoformat(), "first_fraction": 0.2, "last_fraction": 0.3}
            ],
            "is_provisional": False,
        }
        week = valid["weeks"][0]  # type: ignore[index]
        cases = [
            ("missing a field", {"invocation_id": "a"}),
            ("a negative spend", valid | {"list_price_usd": -1.0}),
            ("a spend that isn't a number", valid | {"list_price_usd": float("nan")}),
            ("a reading that isn't finite", valid | {"weeks": [week | {"last_fraction": 1e999}]}),
            ("a subscription without readings", valid | {"weeks": []}),
            (
                "an API key with a provisional charge",
                valid | {"credential_source": "api-key", "weeks": [], "is_provisional": True},
            ),
            ("a provisional flag that isn't a boolean", valid | {"is_provisional": 1}),
            ("a week twice", valid | {"weeks": [week, week]}),
            ("a time without a zone", valid | {"recorded_at": "2026-11-09T12:00:00"}),
        ]
        for label, raw in cases:
            with self.subTest(label):
                self.store.write("ledger.json", 2, {"entries": [raw]})

                with self.assertRaisesRegex(StateStoreUnusable, "malformed entry"):
                    load_entries(self.store, NOW)

    def test_refuses_two_entries_for_one_invocation(self) -> None:
        record_entry(self.store, subscription_entry("a"), NOW)
        document = self.store.read("ledger.json", 2)
        entries = document["entries"]  # type: ignore[index]
        self.store.write("ledger.json", 2, {"entries": entries * 2})  # type: ignore[operator]

        with self.assertRaisesRegex(StateStoreUnusable, "two entries for one invocation"):
            load_entries(self.store, NOW)


class ClearProvisionalChargeTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = StateStore.init(Path(temporary.name))
        self.charge = subscription_entry("a", is_provisional=True)
        record_entry(self.store, self.charge, NOW)

    def test_leaves_the_invocation_charged_what_its_readings_measured(self) -> None:
        terminal = _Terminal("yes\n")

        is_cleared = clear_provisional_charge(self.store, self.charge, NOW, lambda: terminal)

        self.assertTrue(is_cleared)
        self.assertEqual(
            load_entries(self.store, NOW), (replace(self.charge, is_provisional=False),)
        )
        self.assertEqual(find_provisional_charges(self.store, NOW), ())
        shown = terminal.getvalue()
        self.assertIn("Check your subscription's usage first", shown)
        self.assertIn("29% → 31% in the week resetting 2026-11-10 12:00 UTC", shown)
        self.assertTrue(shown.endswith("Type 'yes' to clear the charge: "))

    def test_keeps_the_charge_without_a_confirmation_in_person(self) -> None:
        def no_terminal() -> io.StringIO:
            raise OSError(errno.ENXIO, "No such device or address")

        for label, open_terminal in [
            ("declined", lambda: _Terminal("y\n")),
            ("no terminal", no_terminal),
        ]:
            with self.subTest(label):
                self.assertFalse(
                    clear_provisional_charge(self.store, self.charge, NOW, open_terminal)
                )
                self.assertEqual(find_provisional_charges(self.store, NOW), (self.charge,))
