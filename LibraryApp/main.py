#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 27 14:18:31 2026

@author: ashergabrieljose
"""

# /workspace/main.py
"""Entry point."""
from database import init_db
from ui import LibraryApp


def main():
    init_db()
    app = LibraryApp()
    app.mainloop()


if __name__ == "__main__":
    main()