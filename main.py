#!/usr/bin/env python3
"""GHCC Library Management — top-level launcher.

Delegates to the `library_app` package. Once the project is packaged via
PyInstaller / Briefcase, that bundle's entry point will call the same `main()`.
"""
from library_app.__main__ import main


if __name__ == "__main__":
    main()
