from decimal import Decimal, InvalidOperation

import httpx

RATES_API_URL = "https://rates.example.com/v1/latest"
RATES_API_TIMEOUT_SECONDS = 5


class RatesUnavailableError(Exception):
    """The exchange rates couldn't be fetched. Retrying later may help."""


def get_exchange_rates() -> dict[str, Decimal]:
    """Return what one pound sterling is worth in each currency, keyed by ISO 4217 code."""
    try:
        response = httpx.get(
            RATES_API_URL,
            params={"base": "GBP"},
            timeout=RATES_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RatesUnavailableError("The rates API request failed") from error
    return _decode_rates(body)


def _decode_rates(body: object) -> dict[str, Decimal]:
    match body:
        case {"rates": dict(raw_rates)} if raw_rates:
            pass
        case _:
            raise RatesUnavailableError("The rates API returned a response without rates")
    try:
        rates = {currency: Decimal(str(rate)) for currency, rate in raw_rates.items()}
    except InvalidOperation as error:
        raise RatesUnavailableError("The rates API returned a rate that isn't a number") from error
    if any(rate <= 0 for rate in rates.values()):
        raise RatesUnavailableError("The rates API returned a rate that isn't positive")
    return rates
