from __future__ import annotations

import re
import sqlite3

from ..data import Database
from ..data.repositories import MemberRepository
from ..domain import Member
from ..exceptions import ActiveLoansError, NotFoundError, ValidationError


_NON_DIGIT_RE = re.compile(r"\D")

# Country codes we accept as a leading prefix. The 10-digit national number
# that follows is what we store. Add more here as users report needs.
_COUNTRY_CODES = ("91", "1")  # India, US/Canada


def _normalize_phone(phone: str | None) -> str | None:
    """Normalize an optional phone to a stored 10-digit national number.

    Examples accepted:
        9876543210          → 9876543210
        987-654-3210        → 9876543210
        (987) 654 3210      → 9876543210
        +91 9876543210      → 9876543210  (India country code stripped)
        +1 987-654-3210     → 9876543210  (US country code stripped)
        091 9876543210      → 9876543210  (leading 0 + 91 stripped)

    Empty / None input is treated as "no phone provided" and returns None.
    Anything that doesn't reduce to exactly 10 digits raises ValidationError.
    """
    if phone is None:
        return None
    raw = phone.strip()
    if not raw:
        return None

    digits = _NON_DIGIT_RE.sub("", raw)

    # Strip a leading 0 (national trunk prefix in many regions).
    if len(digits) > 10 and digits.startswith("0"):
        digits = digits.lstrip("0")

    # Strip a leading country code if it produces exactly 10 remaining digits.
    if len(digits) > 10:
        for cc in _COUNTRY_CODES:
            if digits.startswith(cc) and len(digits) - len(cc) == 10:
                digits = digits[len(cc):]
                break

    if len(digits) != 10:
        raise ValidationError(
            "Mobile number must be 10 digits (country code optional)."
        )
    return digits


class MemberService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str, email: str | None, phone: str | None) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("Name is required.")
        phone = _normalize_phone(phone)
        try:
            with self._db.transaction() as conn:
                return MemberRepository(conn).add(
                    name, email or None, phone
                )
        except sqlite3.IntegrityError as e:
            if "email" in str(e).lower():
                raise ValidationError(
                    f"A member with email '{email}' already exists."
                )
            raise

    def update(
        self,
        member_id: int,
        name: str,
        email: str | None,
        phone: str | None,
    ) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("Name is required.")
        phone = _normalize_phone(phone)
        try:
            with self._db.transaction() as conn:
                MemberRepository(conn).update(
                    member_id, name, email or None, phone
                )
        except sqlite3.IntegrityError as e:
            if "email" in str(e).lower():
                raise ValidationError(
                    f"A member with email '{email}' already exists."
                )
            raise

    def delete(self, member_id: int) -> None:
        with self._db.transaction() as conn:
            repo = MemberRepository(conn)
            member = repo.get(member_id)
            if member is None:
                raise NotFoundError(f"Member #{member_id} not found.")
            active = repo.has_active_loans(member_id)
            if active > 0:
                raise ActiveLoansError(
                    f"This member has {active} active loan(s). "
                    "Please ensure all books are returned first."
                )
            repo.delete(member_id)

    def get(self, member_id: int) -> Member | None:
        return MemberRepository(self._db.connection).get(member_id)

    def list_all(self, search: str = "") -> list[Member]:
        return MemberRepository(self._db.connection).list_all(search)
