from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any


@dataclass(frozen=True)
class Language:
    id: int
    name: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Language":
        return cls(id=row["id"], name=row["name"])
