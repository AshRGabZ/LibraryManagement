from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any


@dataclass(frozen=True)
class Category:
    id: int
    name: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Category":
        return cls(id=row["id"], name=row["name"])
