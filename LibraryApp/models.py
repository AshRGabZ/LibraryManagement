#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 27 15:01:29 2026

@author: ashergabrieljose
"""

# /workspace/models.py
"""
Data access / model layer.
Each class encapsulates CRUD operations for its entity.
"""

from datetime import date, timedelta, datetime
from database import get_connection


# --------------------------------------------------------------------------- #
#  Books
# --------------------------------------------------------------------------- #
class BookModel:
    @staticmethod
    def add(title, author, isbn, year, total_copies):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO books (title, author, isbn, year,
                                       total_copies, available_copies)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (title, author, isbn or None, year, total_copies, total_copies),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(book_id, title, author, isbn, year, total_copies):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT total_copies, available_copies FROM books WHERE id=?", (book_id,))
            row = cur.fetchone()
            if not row:
                return False
            loaned_out = row["total_copies"] - row["available_copies"]
            if total_copies < loaned_out:
                raise ValueError(
                    f"Cannot set total copies below {loaned_out} "
                    f"(that many are currently borrowed)."
                )
            new_available = total_copies - loaned_out

            cur.execute(
                """UPDATE books
                   SET title=?, author=?, isbn=?, year=?,
                       total_copies=?, available_copies=?
                   WHERE id=?""",
                (title, author, isbn or None, year, total_copies, new_available, book_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete(book_id):
        """Delete book only if no active loans exist."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) AS cnt FROM loans
                   WHERE book_id=? AND returned_on IS NULL""",
                (book_id,),
            )
            active = cur.fetchone()["cnt"]
            if active > 0:
                raise ValueError(
                    f"Cannot delete: this book has {active} active loan(s). "
                    f"Please ensure all copies are returned first."
                )
            cur.execute("DELETE FROM loans WHERE book_id=?", (book_id,))
            cur.execute("DELETE FROM books WHERE id=?", (book_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def has_active_loans(book_id):
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT COUNT(*) AS cnt FROM loans
                   WHERE book_id=? AND returned_on IS NULL""",
                (book_id,),
            )
            return cur.fetchone()["cnt"] > 0
        finally:
            conn.close()

    @staticmethod
    def get(book_id):
        conn = get_connection()
        try:
            cur = conn.execute("SELECT * FROM books WHERE id=?", (book_id,))
            return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def list_all(search=""):
        conn = get_connection()
        try:
            if search:
                like = f"%{search}%"
                cur = conn.execute(
                    """SELECT * FROM books
                       WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ?
                       ORDER BY title""",
                    (like, like, like),
                )
            else:
                cur = conn.execute("SELECT * FROM books ORDER BY title")
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def stats():
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT COUNT(*) AS total,
                          COALESCE(SUM(total_copies), 0)     AS copies,
                          COALESCE(SUM(available_copies), 0) AS available
                   FROM books"""
            )
            return cur.fetchone()
        finally:
            conn.close()


# --------------------------------------------------------------------------- #
#  Members
# --------------------------------------------------------------------------- #
class MemberModel:
    @staticmethod
    def add(name, email, phone):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO members (name, email, phone) VALUES (?, ?, ?)",
                (name, email or None, phone or None),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(member_id, name, email, phone):
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE members SET name=?, email=?, phone=? WHERE id=?",
                (name, email or None, phone or None, member_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(member_id):
        """Delete member only if no active loans exist."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) AS cnt FROM loans
                   WHERE member_id=? AND returned_on IS NULL""",
                (member_id,),
            )
            active = cur.fetchone()["cnt"]
            if active > 0:
                raise ValueError(
                    f"Cannot delete: this member has {active} active loan(s). "
                    f"Please ensure all books are returned first."
                )
            cur.execute("DELETE FROM loans WHERE member_id=?", (member_id,))
            cur.execute("DELETE FROM members WHERE id=?", (member_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def has_active_loans(member_id):
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT COUNT(*) AS cnt FROM loans
                   WHERE member_id=? AND returned_on IS NULL""",
                (member_id,),
            )
            return cur.fetchone()["cnt"] > 0
        finally:
            conn.close()

    @staticmethod
    def get(member_id):
        conn = get_connection()
        try:
            cur = conn.execute("SELECT * FROM members WHERE id=?", (member_id,))
            return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def list_all(search=""):
        conn = get_connection()
        try:
            if search:
                like = f"%{search}%"
                cur = conn.execute(
                    """SELECT * FROM members
                       WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?
                       ORDER BY name""",
                    (like, like, like),
                )
            else:
                cur = conn.execute("SELECT * FROM members ORDER BY name")
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def count():
        conn = get_connection()
        try:
            cur = conn.execute("SELECT COUNT(*) AS cnt FROM members")
            return cur.fetchone()["cnt"]
        finally:
            conn.close()


# --------------------------------------------------------------------------- #
#  Loans (borrow / return / renew)
# --------------------------------------------------------------------------- #
class LoanModel:
    DEFAULT_LOAN_DAYS = 14
    MAX_RENEWALS = 3
    DEFAULT_RENEW_DAYS = 7

    @staticmethod
    def borrow(book_id, member_id, loan_days=DEFAULT_LOAN_DAYS):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT available_copies FROM books WHERE id=?", (book_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Book not found.")
            if row["available_copies"] <= 0:
                raise ValueError("No copies available for this book.")

            borrowed_on = date.today()
            due_on = borrowed_on + timedelta(days=loan_days)

            cur.execute(
                """INSERT INTO loans (book_id, member_id, borrowed_on, due_on)
                   VALUES (?, ?, ?, ?)""",
                (book_id, member_id, borrowed_on.isoformat(), due_on.isoformat()),
            )
            cur.execute(
                "UPDATE books SET available_copies = available_copies - 1 WHERE id=?",
                (book_id,),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def return_loan(loan_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM loans WHERE id=?", (loan_id,))
            loan = cur.fetchone()
            if not loan:
                raise ValueError("Loan record not found.")
            if loan["returned_on"]:
                raise ValueError("This loan has already been returned.")

            cur.execute(
                "UPDATE loans SET returned_on=? WHERE id=?",
                (date.today().isoformat(), loan_id),
            )
            cur.execute(
                "UPDATE books SET available_copies = available_copies + 1 WHERE id=?",
                (loan["book_id"],),
            )
            conn.commit()
        finally:
            conn.close()
    
    @staticmethod
    def renew(loan_id, extra_days=14, max_renewals=3):
        """Extend the due date and increment renew_count."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM loans WHERE id=?", (loan_id,))
            loan = cur.fetchone()
            if not loan:
                raise ValueError("Loan not found.")
            if loan["returned_on"]:
                raise ValueError("Cannot renew a returned loan.")
            if loan["renew_count"] >= max_renewals:
                raise ValueError(f"Maximum renewals ({max_renewals}) reached.")

            current_due = date.fromisoformat(loan["due_on"]) if loan["due_on"] else date.today()
            base = max(current_due, date.today())
            new_due = base + timedelta(days=extra_days)

            cur.execute(
                "UPDATE loans SET due_on=?, renew_count = renew_count + 1 WHERE id=?",
                (new_due.isoformat(), loan_id),
            )
            conn.commit()
            return new_due
        finally:
            conn.close()

    @staticmethod
    def get(loan_id):
        """Fetch a single loan record with joined book/member info."""
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT loans.*,
                          books.title  AS book_title,
                          members.name AS member_name
                   FROM loans
                   JOIN books   ON books.id   = loans.book_id
                   JOIN members ON members.id = loans.member_id
                   WHERE loans.id=?""",
                (loan_id,),
            )
            return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def list_all(active_only=False, search=""):
        conn = get_connection()
        try:
            sql = """SELECT loans.id, books.title AS book_title,
                            members.name  AS member_name,
                            loans.borrowed_on, loans.due_on, loans.returned_on,
                            loans.renew_count,
                            loans.book_id, loans.member_id
                     FROM loans
                     JOIN books   ON books.id   = loans.book_id
                     JOIN members ON members.id = loans.member_id"""
            clauses, params = [], []
            if active_only:
                clauses.append("loans.returned_on IS NULL")
            if search:
                like = f"%{search}%"
                clauses.append("(books.title LIKE ? OR members.name LIKE ?)")
                params.extend([like, like])
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY loans.returned_on IS NOT NULL, loans.due_on"
            cur = conn.execute(sql, params)
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def stats():
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT
                     SUM(CASE WHEN returned_on IS NULL THEN 1 ELSE 0 END) AS active,
                     SUM(CASE WHEN returned_on IS NULL
                              AND due_on < DATE('now') THEN 1 ELSE 0 END) AS overdue,
                     COUNT(*) AS total
                   FROM loans"""
            )
            return cur.fetchone()
        finally:
            conn.close()