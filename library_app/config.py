"""Application-wide configuration constants.

Centralizing constants here avoids magic numbers scattered across the codebase
and makes the application easier to package — paths can be redirected to user
home directories when distributed as a desktop app.
"""
from __future__ import annotations

import sys
from pathlib import Path


# ---------------------------------------------------------------- paths ----- #

def _default_data_dir() -> Path:
    """Return the platform-appropriate location for application data.

    When packaged as a desktop app, data must live in a writable user dir,
    not next to the (potentially read-only) bundled executable.
    """
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "GHCCLibrary"
    if sys.platform.startswith("win"):
        import os
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "GHCCLibrary"
    # Linux / other Unix — XDG spec
    import os
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "GHCCLibrary"


# Database location, in priority order:
#   1. LIBRARY_APP_DB_PATH env var — explicit override (any environment).
#   2. Packaged build (PyInstaller sets sys.frozen) — per-user data dir, since
#      the bundle itself is read-only and a one-file build's temp dir is wiped
#      on exit. This is what makes the .exe / .app persist data correctly.
#   3. Development — project-relative, so the DB is easy to find and inspect.
import os
_env_db = os.environ.get("LIBRARY_APP_DB_PATH")
if _env_db:
    DB_PATH = Path(_env_db)
elif getattr(sys, "frozen", False):
    DB_PATH = _default_data_dir() / "library.db"
else:
    DB_PATH = Path(__file__).resolve().parent.parent / "library.db"


# ---------------------------------------------------------------- loans ----- #

DEFAULT_LOAN_DAYS: int = 14
MAX_RENEWALS: int = 3
DEFAULT_RENEW_DAYS: int = 7


# ---------------------------------------------------------------- ui   ----- #

WINDOW_TITLE: str = "📚 GHCC Library Management"
WINDOW_GEOMETRY: str = "1280x720"
WINDOW_MIN_SIZE: tuple[int, int] = (1000, 600)

# Name printed on the header of every book label. Change this for a different
# branch/branding.
LIBRARY_NAME: str = "GHCC Pune Library"


# ---------------------------------------------------------- notifications -- #

# Stored phone numbers are 10 digits (national). wa.me requires the country
# code prefix. Change this if your library serves a different region.
DEFAULT_COUNTRY_CODE: str = "91"  # India

# Message body sent via wa.me. Uses .format() placeholders the
# NotificationService fills in. Edit freely — tone, branding, language all
# live here, not in code.
WHATSAPP_TEMPLATE: str = (
    "Hi {name}, this is a reminder from GHCC Library.\n\n"
    "You currently have these book(s) borrowed:\n"
    "{book_list}\n\n"
    "Please return/renew them at your earliest convenience.\n\n"
    "Thanks!"
)
