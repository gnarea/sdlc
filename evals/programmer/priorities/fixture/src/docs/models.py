from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    name: str


@dataclass(frozen=True)
class Document:
    id: int
    title: str
    owner_id: int
    space_id: int
