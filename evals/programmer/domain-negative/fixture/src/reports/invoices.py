from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class InvoiceRow:
    number: int
    issued_on: date
    due_on: date
    total_pence: int

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError(f"Invoice number must be positive (got {self.number})")
        if self.total_pence < 0:
            raise ValueError(f"Invoice total must not be negative (got {self.total_pence})")
