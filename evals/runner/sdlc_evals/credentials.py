"""The credential that each invocation passes to the harness: exactly one, from one source."""

import enum
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from .state.store import StateStore
from .state.subscription_token import load_token

API_KEY_ENVIRONMENT_VARIABLE = "ANTHROPIC_API_KEY"
OAUTH_TOKEN_ENVIRONMENT_VARIABLE = "CLAUDE_CODE_OAUTH_TOKEN"
# Standard API keys only: an admin key reaches far more than inference.
_API_KEY_PATTERN = re.compile(r"sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{32,512}")


class CredentialSource(enum.StrEnum):
    SUBSCRIPTION = "subscription"
    API_KEY = "api-key"


@dataclass(frozen=True)
class Credential:
    """A credential and the variable that hands it to the harness. Only the source is ever recorded."""

    source: CredentialSource
    environment_variable: str
    value: str = field(repr=False)


class CredentialUnavailable(Exception):
    """The chosen source has no usable credential. Retrying won't help until the operator provides
    one.
    """


def load_credential(
    source: CredentialSource, store: StateStore, environment: Mapping[str, str], now: datetime
) -> Credential:
    if source is CredentialSource.SUBSCRIPTION:
        return _load_subscription_token(store, now)
    return _load_api_key(environment)


def _load_subscription_token(store: StateStore, now: datetime) -> Credential:
    token = load_token(store, now)
    if token is None:
        raise CredentialUnavailable(
            "No unexpired subscription token is stored: run `claude setup-token`, then the wrapper's store-token command"
        )
    return Credential(CredentialSource.SUBSCRIPTION, OAUTH_TOKEN_ENVIRONMENT_VARIABLE, token.value)


def _load_api_key(environment: Mapping[str, str]) -> Credential:
    key = environment.get(API_KEY_ENVIRONMENT_VARIABLE, "")
    if not _API_KEY_PATTERN.fullmatch(key):
        raise CredentialUnavailable(
            f"{API_KEY_ENVIRONMENT_VARIABLE} must hold a standard API key (sk-ant-api…), never an admin key"
        )
    return Credential(CredentialSource.API_KEY, API_KEY_ENVIRONMENT_VARIABLE, key)
