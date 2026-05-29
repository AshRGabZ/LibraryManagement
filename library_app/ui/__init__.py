"""Tkinter presentation layer.

Pure UI code. Talks to the application via the Services container injected at
construction time. No SQL, no database knowledge.
"""

from .app import LibraryApp

__all__ = ["LibraryApp"]
