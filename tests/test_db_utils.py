"""Unit tests for :mod:`db_utils`.

These tests run against real in-memory SQLite databases (no mocks) so they
exercise the exact SQL the GUI issues.
"""

import os
import sqlite3
import tempfile
import unittest

import db_utils


class QuoteIdentifierTests(unittest.TestCase):
    def test_plain_name(self):
        self.assertEqual(db_utils.quote_identifier("users"), '"users"')

    def test_embedded_quote_is_doubled(self):
        self.assertEqual(db_utils.quote_identifier('we"ird'), '"we""ird"')

    def test_rejects_empty_and_nul(self):
        with self.assertRaises(ValueError):
            db_utils.quote_identifier("")
        with self.assertRaises(ValueError):
            db_utils.quote_identifier("a\x00b")


class TableIntrospectionTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT)")
        self.conn.execute("CREATE TABLE notes (body TEXT)")  # no primary key
        # AUTOINCREMENT makes SQLite create the internal `sqlite_sequence` table,
        # which must be hidden from the explorer.
        self.conn.execute("CREATE TABLE seq (id INTEGER PRIMARY KEY AUTOINCREMENT, v TEXT)")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_list_tables_excludes_internal(self):
        self.assertEqual(db_utils.list_tables(self.conn), ["notes", "people", "seq"])

    def test_primary_key_detection(self):
        cols = db_utils.table_columns(self.conn, "people")
        self.assertEqual(db_utils.primary_key_column(cols), "id")

    def test_primary_key_absent(self):
        cols = db_utils.table_columns(self.conn, "notes")
        self.assertIsNone(db_utils.primary_key_column(cols))

    def test_quoted_table_with_special_name(self):
        self.conn.execute('CREATE TABLE "odd name" ("a b" INTEGER)')
        self.conn.execute('INSERT INTO "odd name" VALUES (1)')
        cols = db_utils.table_columns(self.conn, "odd name")
        self.assertEqual(cols[0][1], "a b")


class SearchClauseTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE t (name TEXT, note TEXT)")
        self.conn.executemany(
            "INSERT INTO t VALUES (?, ?)",
            [("Alice", "hello"), ("bob", "100% done"), ("Carol", None)],
        )
        self.conn.commit()
        self.cols = db_utils.table_columns(self.conn, "t")

    def tearDown(self):
        self.conn.close()

    def _search(self, text):
        where, params = db_utils.build_search_clause(self.cols, text)
        sql = f"SELECT name FROM t WHERE {where} ORDER BY name"
        return [r[0] for r in self.conn.execute(sql, params)]

    def test_empty_search_returns_no_clause(self):
        self.assertEqual(db_utils.build_search_clause(self.cols, ""), ("", []))

    def test_case_insensitive_contains(self):
        self.assertEqual(self._search("ali"), ["Alice"])

    def test_percent_is_literal_not_wildcard(self):
        # '%' in the input must match the literal percent, not "any string".
        self.assertEqual(self._search("100%"), ["bob"])


class PaginationTests(unittest.TestCase):
    def test_offset_within_range(self):
        self.assertEqual(db_utils.page_offset(1, 100, 250), (100, 1))

    def test_page_clamped_to_last(self):
        self.assertEqual(db_utils.page_offset(99, 100, 250), (200, 2))

    def test_empty_table(self):
        self.assertEqual(db_utils.page_offset(0, 100, 0), (0, 0))

    def test_negative_page_clamped(self):
        self.assertEqual(db_utils.page_offset(-5, 100, 250), (0, 0))


class FetchTablePageTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        self.conn.executemany(
            "INSERT INTO items (id, name) VALUES (?, ?)",
            [(i, f"item{i}") for i in range(1, 251)],
        )
        self.conn.execute("CREATE TABLE no_pk (val TEXT)")
        self.conn.executemany("INSERT INTO no_pk VALUES (?)", [("a",), ("b",), ("c",)])
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_first_page_and_total(self):
        cols = db_utils.table_columns(self.conn, "items")
        rows, ids, total, page = db_utils.fetch_table_page(
            self.conn, "items", cols, page=0, page_size=100
        )
        self.assertEqual(total, 250)
        self.assertEqual(page, 0)
        self.assertEqual(len(rows), 100)
        self.assertEqual(ids[0], "1")

    def test_last_page_clamped(self):
        cols = db_utils.table_columns(self.conn, "items")
        rows, _ids, total, page = db_utils.fetch_table_page(
            self.conn, "items", cols, page=99, page_size=100
        )
        self.assertEqual(total, 250)
        self.assertEqual(page, 2)
        self.assertEqual(len(rows), 50)

    def test_search_filters_rows(self):
        cols = db_utils.table_columns(self.conn, "items")
        rows, ids, total, _page = db_utils.fetch_table_page(
            self.conn, "items", cols, page_size=500, search_text="item1"
        )
        # item1, item10..item19, item100..item199 => 111 matches in total
        self.assertEqual(total, 111)
        self.assertEqual(len(rows), 111)
        self.assertIn("1", ids)

    def test_table_without_pk_uses_rowid(self):
        cols = db_utils.table_columns(self.conn, "no_pk")
        rows, ids, total, _page = db_utils.fetch_table_page(self.conn, "no_pk", cols)
        self.assertEqual(total, 3)
        self.assertEqual(rows[0], ("a",))
        self.assertEqual(ids, ["1", "2", "3"])


class SplitStatementsTests(unittest.TestCase):
    def test_multiple_statements(self):
        script = "CREATE TABLE t (a);\nINSERT INTO t VALUES (1);\n"
        self.assertEqual(len(db_utils.split_statements(script)), 2)

    def test_semicolon_inside_string_literal(self):
        script = "INSERT INTO t VALUES ('a;b');"
        self.assertEqual(db_utils.split_statements(script), ["INSERT INTO t VALUES ('a;b');"])

    def test_trailing_statement_without_semicolon(self):
        self.assertEqual(db_utils.split_statements("SELECT 1"), ["SELECT 1"])


class ExportCsvTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
        self.conn.executemany(
            "INSERT INTO t VALUES (?, ?)", [(1, "日本語"), (2, "ascii")]
        )
        self.conn.commit()
        self.cols = db_utils.table_columns(self.conn, "t")

    def tearDown(self):
        self.conn.close()

    def test_export_writes_bom_header_and_rows(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            count = db_utils.export_table_to_csv(self.conn, "t", self.cols, path)
            self.assertEqual(count, 2)
            with open(path, "rb") as fh:
                raw = fh.read()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))  # UTF-8 BOM
            text = raw.decode("utf-8-sig")
            self.assertIn("id,name", text)
            self.assertIn("日本語", text)
        finally:
            os.remove(path)


class RowMutationSqlTests(unittest.TestCase):
    """Mirror the UPDATE/DELETE SQL the GUI builds to prove row targeting works.

    The GUI cannot run headlessly (no Tk display), so these tests reproduce the
    exact statements it issues, including the rowid fallback for tables without
    a primary key.
    """

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE pk_table (id INTEGER PRIMARY KEY, name TEXT)")
        self.conn.execute("INSERT INTO pk_table VALUES (7, 'old')")
        self.conn.execute("CREATE TABLE nopk (name TEXT)")
        self.conn.executemany("INSERT INTO nopk VALUES (?)", [("a",), ("b",), ("c",)])
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_update_by_primary_key(self):
        table = db_utils.quote_identifier("pk_table")
        sql = (f"UPDATE {table} SET {db_utils.quote_identifier('name')} = ? "
               f"WHERE {db_utils.quote_identifier('id')} = ?")
        self.conn.execute(sql, ("new", "7"))
        self.conn.commit()
        self.assertEqual(
            self.conn.execute("SELECT name FROM pk_table WHERE id = 7").fetchone()[0],
            "new",
        )

    def test_update_by_rowid_when_no_pk(self):
        # The GUI keys rows on `rowid` for tables without a primary key.
        table = db_utils.quote_identifier("nopk")
        sql = f"UPDATE {table} SET {db_utils.quote_identifier('name')} = ? WHERE rowid = ?"
        self.conn.execute(sql, ("z", "2"))
        self.conn.commit()
        self.assertEqual(
            [r[0] for r in self.conn.execute("SELECT name FROM nopk ORDER BY rowid")],
            ["a", "z", "c"],
        )

    def test_delete_by_rowid_when_no_pk(self):
        table = db_utils.quote_identifier("nopk")
        self.conn.execute(f"DELETE FROM {table} WHERE rowid = ?", ("2",))
        self.conn.commit()
        self.assertEqual(
            [r[0] for r in self.conn.execute("SELECT name FROM nopk ORDER BY rowid")],
            ["a", "c"],
        )


if __name__ == "__main__":
    unittest.main()
