from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Member:
    id: int
    name: str
    email: str | None
    phone: str | None
    joined: str  # ISO date string

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Member":
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            joined=row["joined"],
        )
