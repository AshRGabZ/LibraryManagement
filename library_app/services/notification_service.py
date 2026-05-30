"""Notification service — outbound messaging to library members.

Today the only channel is WhatsApp via the wa.me deeplink (free, uses the
librarian's own WhatsApp Web/Desktop login, zero account risk). Other channels
(SMS, email, Meta Cloud API) plug in here behind the same compose/send seam.

The split between `whatsapp_url()` (pure, testable) and `open_whatsapp()`
(side-effecting) lets unit tests assert on the URL without touching the OS.
"""
from __future__ import annotations

import logging
import urllib.parse
import webbrowser
from typing import Iterable

from ..config import DEFAULT_COUNTRY_CODE, WHATSAPP_TEMPLATE
from ..domain import LoanWithDetails, Member
from ..exceptions import ValidationError


_log = logging.getLogger(__name__)


class NotificationService:
    """WhatsApp message composition + dispatch via wa.me deeplinks."""

    def __init__(
        self,
        default_country_code: str = DEFAULT_COUNTRY_CODE,
        template: str = WHATSAPP_TEMPLATE,
    ) -> None:
        self._country_code = default_country_code
        self._template = template

    # ------------------------------------------------------------ compose #

    def compose_message(
        self,
        member: Member,
        loans: Iterable[LoanWithDetails],
    ) -> str:
        """Render the WhatsApp message body for a member and their loans.

        Only includes active (not-returned) loans — there's no value in
        reminding someone about books they've already returned.
        """
        active = [ln for ln in loans if not ln.is_returned]
        if active:
            lines = []
            for ln in active:
                if ln.is_overdue:
                    days = abs(ln.days_left or 0)
                    suffix = f" — OVERDUE by {days} day{'s' if days != 1 else ''}"
                elif ln.days_left is not None:
                    if ln.days_left == 0:
                        suffix = " — due today"
                    else:
                        suffix = f" — due in {ln.days_left} day{'s' if ln.days_left != 1 else ''}"
                else:
                    suffix = ""
                # Include the specific copy's serial when available — helps
                # the member find the right book on their shelf when several
                # copies were borrowed.
                title = ln.book_title
                if ln.serial_number:
                    title = f"{title} [{ln.serial_number}]"
                lines.append(f"• {title} (due {ln.due_on or '—'}){suffix}")
            book_list = "\n".join(lines)
        else:
            book_list = "(no active loans)"
        return self._template.format(name=member.name, book_list=book_list)

    # ------------------------------------------------------------- urls   #

    def _phone_with_country_code(self, phone: str) -> str:
        """Prepend the configured country code unless one is already present.

        Stored phones are 10 digits (per MemberService normalization). If a
        future migration ever stores international numbers, this still
        produces the correct wa.me path.
        """
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) > 10:
            return digits  # already international
        return self._country_code + digits

    def whatsapp_url(self, phone: str, message: str) -> str:
        """Build a wa.me URL. Pure function — easy to unit test."""
        intl = self._phone_with_country_code(phone)
        encoded = urllib.parse.quote(message, safe="")
        return f"https://wa.me/{intl}?text={encoded}"

    # ------------------------------------------------------------- send   #

    def open_whatsapp(
        self,
        member: Member,
        loans: Iterable[LoanWithDetails],
    ) -> str:
        """Open the default WhatsApp client with a pre-filled message.

        Raises ValidationError if the member has no phone number. Returns the
        URL that was opened, for logging / testing.
        """
        if not member.phone:
            raise ValidationError(
                f"{member.name} has no phone number on file. "
                "Add one in Admin → Manage Members."
            )
        message = self.compose_message(member, loans)
        url = self.whatsapp_url(member.phone, message)
        _log.info("Opening WhatsApp for %s (phone %s)", member.name, member.phone)
        webbrowser.open(url)
        return url
