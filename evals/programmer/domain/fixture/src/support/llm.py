import httpx

LLM_API_URL = "https://llm.internal.example.com/v1/complete"
LLM_TIMEOUT_SECONDS = 30


class LLMError(Exception):
    """The LLM service couldn't be reached, or it responded unexpectedly.

    Retrying later may help, since the service may have been briefly unavailable.
    """


class LLMClient:
    def __init__(self, http_client: httpx.Client) -> None:
        self._http_client = http_client

    def complete(self, system_prompt: str, user_message: str) -> str:
        """Return the model's reply to `user_message`, following `system_prompt`."""
        try:
            response = self._http_client.post(
                LLM_API_URL,
                json={"system": system_prompt, "message": user_message},
                timeout=LLM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise LLMError("The LLM service request failed") from error
        match body:
            case {"reply": str(reply)}:
                return reply
        raise LLMError("The LLM service returned a response without a reply")
