import json
from pathlib import Path

SAMPLE_ORDERS = Path(__file__).parent / "sample_orders.json"


def load_orders() -> list[dict]:
    return json.loads(SAMPLE_ORDERS.read_text())


def find_order(order_id: str) -> dict | None:
    return next((order for order in load_orders() if order["id"] == order_id), None)
