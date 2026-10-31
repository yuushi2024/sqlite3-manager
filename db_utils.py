"""Reusable SQLite helpers for the SQLite Studio GUI.

Everything in this module is free of Tkinter so it can be unit tested without a
display.  The GUI layer in :mod:`main` only deals with widgets and delegates the
database work to the functions below.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import sys
from typing import Any, Iterable, Sequence

_NUL = "\x00"


def quote_identifier(name: str) -> str:
    """Return *name* as a safely quoted SQLite identifier.

    Identifiers (table/column names) cannot be passed as bound parameters, so
    they must be quoted.  Wrapping in double quotes with embedded quotes doubled
    handles reserved words, spaces and other special characters, and prevents
    the values from being interpreted as SQL.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("identifier must be a non-empty string")
    if _NUL in name:
        raise ValueError("identifier must not contain NUL bytes")
    return '"' + name.replace('"', '""') + '"'


def list_tables(conn: sqlite3.Connection) -> list[str]:
    """Return user table names, excluding SQLite's internal ``sqlite_*`` tables."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\' "
        "ORDER BY name"
    )
    return [row[0] for row in cur.fetchall()]


def table_columns(conn: sqlite3.Connection, table: str) -> list[tuple]:
    """Return ``PRAGMA table_info`` rows for *table*.

    Each row is ``(cid, name, type, notnull, dflt_value, pk)``.
    """
    return conn.execute(
        f"PRAGMA table_info({quote_identifier(table)})"
    ).fetchall()


def primary_key_column(columns: Sequence[tuple]) -> str | None:
    """Return the name of the single primary-key column, or ``None``."""
    keys = [col[1] for col in columns if len(col) > 5 and col[5]]
    return keys[0] if len(keys) == 1 else None


def _escape_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def build_search_clause(
    columns: Sequence[tuple], search_text: str
) -> tuple[str, list[str]]:
    """Build a ``WHERE`` fragment and parameters for a "contains" search.

    Every column is cast to text and matched case-insensitively.  LIKE
    wildcards in the user's input are escaped so they are treated literally.
    """
    names = [col[1] for col in columns]
    if not search_text or not names:
        return "", []

    fragment = " OR ".join(
        f"CAST({quote_identifier(name)} AS TEXT) LIKE ? ESCAPE '\\'"
        for name in names
    )
    like = f"%{_escape_like(search_text)}%"
    return fragment, [like] * len(names)


def page_offset(page: int, page_size: int, total: int) -> tuple[int, int]:
    """Clamp *page* to the valid range and return ``(offset, page)``.

    Keeps the pagination from running past the last page (e.g. after rows were
    deleted) and handles the empty-table case.
    """
    if page_size <= 0:
        page_size = 1
    max_page = max(0, (total - 1) // page_size) if total else 0
    page = min(max(page, 0), max_page)
    return page * page_size, page


def fetch_table_page(
    conn: sqlite3.Connection,
    table: str,
    columns: Sequence[tuple],
    page: int = 0,
    page_size: int = 100,
    search_text: str = "",
) -> tuple[list[tuple], list[str], int, int]:
    """Fetch one page of a table for display.

    Returns ``(rows, row_ids, total, page)`` where *row_ids* are stable strings
    identifying each row (the primary-key value, or SQLite's ``rowid`` when
    there is no single-column primary key) so edits and deletes can target them.
    """
    table_q = quote_identifier(table)
    where, params = build_search_clause(columns, search_text)

    count_sql = f"SELECT COUNT(*) FROM {table_q}"
    if where:
        count_sql += f" WHERE {where}"
    total = conn.execute(count_sql, params).fetchone()[0]

    offset, page = page_offset(page, page_size, total)

    pk = primary_key_column(columns)
    # Use the implicit rowid when no single column identifies the row.
    prefix = "rowid AS __rowid__, " if pk is None else ""
    data_sql = f"SELECT {prefix}* FROM {table_q}"
    if where:
        data_sql += f" WHERE {where}"
    data_sql += " LIMIT ? OFFSET ?"
    raw = conn.execute(data_sql, [*params, page_size, offset]).fetchall()

    pk_idx = [col[1] for col in columns].index(pk) if pk else -1
    rows: list[tuple] = []
    row_ids: list[str] = []
    for record in raw:
        if pk is None:
            row_ids.append(str(record[0]))
            rows.append(tuple(record[1:]))
        else:
            values = tuple(record)
            row_ids.append(str(values[pk_idx]))
            rows.append(values)
    return rows, row_ids, total, page


def split_statements(sql: str) -> list[str]:
    """Split a SQL script into individual statements.

    Uses ``sqlite3.complete_statement`` so semicolons inside string literals or
    triggers do not break the script apart.
    """
    statements: list[str] = []
    buffer = ""
    def has_sql(fragment: str) -> bool:
        return not re.fullmatch(r"(?:\s|--[^\n]*(?:\n|$)|/\*.*?(?:\*/|$)|;)*", fragment, re.DOTALL)

    for char in sql:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            stripped = buffer.strip()
            if has_sql(stripped):
                statements.append(stripped)
            buffer = ""
    if has_sql(buffer):
        statements.append(buffer.strip())
    return statements


def export_table_to_csv(
    conn: sqlite3.Connection,
    table: str,
    columns: Sequence[tuple],
    path: str,
    encoding: str = "utf-8-sig",
) -> int:
    """Write *table* to *path* as CSV and return the number of data rows.

    ``utf-8-sig`` adds a BOM so Excel opens Japanese text correctly.
    """
    names = [col[1] for col in columns]
    cur = conn.execute(f"SELECT * FROM {quote_identifier(table)}")
    rows = cur.fetchall()
    with open(path, "w", newline="", encoding=encoding) as handle:
        writer = csv.writer(handle)
        writer.writerow(names)
        writer.writerows(rows)
    return len(rows)


def enable_dpi_awareness() -> bool:
    """Best-effort high-DPI awareness on Windows; a no-op elsewhere."""
    if sys.platform != "win32":
        return False
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
        return True
    except Exception:
        return False


def pick_font_family(root: Any, candidates: Iterable[str], fallback: str = "TkDefaultFont") -> str:
    """Return the first font in *candidates* installed on the system."""
    from tkinter import font as tkfont

    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return name
    return fallback
