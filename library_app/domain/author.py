from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any


@dataclass(frozen=True)
class Author:
    id: int
    name: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Author":
        return cls(id=row["id"], name=row["name"])
