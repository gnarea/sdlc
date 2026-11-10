from decimal import ROUND_HALF_EVEN, Decimal

from pricing.rates import get_exchange_rates

PENCE_PER_POUND = 100


class UnsupportedCurrencyError(Exception):
    """The rates API doesn't quote the currency. Retrying won't help."""


def quote_price(price_pence: int, currency: str) -> Decimal:
    """Return a price in pence sterling converted to `currency`, rounded to two decimal places."""
    rates = get_exchange_rates()
    if currency not in rates:
        raise UnsupportedCurrencyError(f"No exchange rate for the currency (got {currency!r})")
    pounds = Decimal(price_pence) / PENCE_PER_POUND
    return (pounds * rates[currency]).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
