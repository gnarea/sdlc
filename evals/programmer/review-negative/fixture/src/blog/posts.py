from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Post:
    title: str
    published_on: date
    body: str
