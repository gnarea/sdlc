from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Message:
    author: str
    sent_at: datetime
    body: str


@dataclass(frozen=True)
class Ticket:
    id: int
    subject: str
    messages: tuple[Message, ...]
