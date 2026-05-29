"""Entry point: `python -m library_app`."""
from __future__ import annotations

import logging
import sys

from .config import DB_PATH
from .data import Database
from .logging_setup import configure_logging
from .services import Services
from .ui import LibraryApp


def main() -> None:
    configure_logging(DB_PATH.parent)
    log = logging.getLogger(__name__)
    log.info("Starting application")

    db = Database(DB_PATH)
    try:
        services = Services.build(db)
        app = LibraryApp(services)
        app.mainloop()
    except Exception:
        log.exception("Unhandled exception in main loop")
        raise
    finally:
        db.close()
        log.info("Application stopped")


if __name__ == "__main__":
    main()
