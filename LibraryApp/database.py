#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 27 14:16:20 2026

@author: ashergabrieljose
"""

# /workspace/database.py
"""SQLite connection and schema."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "library.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            year INTEGER,
            total_copies INTEGER NOT NULL DEFAULT 1,
            available_copies INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            joined TEXT DEFAULT (DATE('now'))
        );
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            borrowed_on TEXT NOT NULL DEFAULT (DATE('now')),
            due_on TEXT,
            returned_on TEXT,
            renew_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE RESTRICT
        );
    """)
    # Migration: add renew_count if missing (older DBs)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(loans)")]
    if "renew_count" not in cols:
        conn.execute("ALTER TABLE loans ADD COLUMN renew_count INTEGER NOT NULL DEFAULT 0")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"DB ready: {DB_PATH}")
