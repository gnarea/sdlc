from http import HTTPStatus

import requests

BILLING_API_URL = "https://billing.example.com/v1"


class BillingError(Exception):
    """The billing API couldn't be reached, or it responded unexpectedly.

    Retrying later may help, since the API may have been briefly unavailable.
    """


class BillingClient:
    def __init__(self, api_key: str) -> None:
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"

    def find_customer_id(self, email: str) -> str | None:
        """Return the ID of the billing customer registered under `email`, if any."""
        try:
            response = self._session.post(
                f"{BILLING_API_URL}/customers/search",
                json={"email": email},
            )
            if response.status_code == HTTPStatus.NOT_FOUND:
                return None
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as error:
            raise BillingError("The billing API request failed") from error
        return _decode_customer_id(body)


def _decode_customer_id(body: object) -> str:
    match body:
        case {"id": str(customer_id)} if customer_id:
            return customer_id
    raise BillingError("The billing API returned a customer without a valid ID")
