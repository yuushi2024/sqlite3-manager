"""Headless tests of the GUI's SQLite interactions."""

import sqlite3
import unittest
from unittest.mock import MagicMock, patch

from main import ModernSQLiteStudio


class StudioInteractionTests(unittest.TestCase):
    def setUp(self):
        self.app = ModernSQLiteStudio.__new__(ModernSQLiteStudio)
        self.app.conn = sqlite3.connect(":memory:")
        self.app.conn.execute('CREATE TABLE "001" (id INTEGER PRIMARY KEY, value TEXT)')
        self.app.conn.commit()
        self.app.current_table = "001"
        self.app.load_data = MagicMock()
        self.app.txt_sql = MagicMock()
        self.app.tree_sql = MagicMock()
        self.app.sidebar_tree = MagicMock()
        self.app.search_var = MagicMock()

    def tearDown(self):
        self.app.conn.close()

    def run_script(self, sql):
        self.app.txt_sql.get.return_value = sql
        with patch("main.messagebox.showinfo"), patch("main.messagebox.showerror") as error:
            self.app.run_sql()
        return error

    def test_sidebar_ids_preserve_numeric_table_name(self):
        self.app.sidebar_tree.insert.return_value = "root"
        self.app.refresh_sidebar()
        self.app.sidebar_tree.insert.assert_any_call("root", "end", iid="table:001", text=" 📄 001")
        self.app.sidebar_tree.selection.return_value = ("table:001",)
        self.app.on_table_select(None)
        self.assertEqual(self.app.current_table, "001")
        self.assertIsInstance(self.app.current_table, str)
        self.assertEqual(self.app.primary_key, "id")
        self.app.load_data.assert_called_once()
        self.app.sidebar_tree.selection.return_value = ("root",)
        self.app.on_table_select(None)
        self.app.load_data.assert_called_once()

    def test_write_followed_by_select_is_committed_and_displayed(self):
        error = self.run_script('INSERT INTO "001" VALUES (1, "hello"); SELECT * FROM "001"; -- end')
        error.assert_not_called()
        self.assertFalse(self.app.conn.in_transaction)
        self.app.tree_sql.insert.assert_called_once_with("", "end", values=(1, "hello"))
        self.app.load_data.assert_called_once()

    def test_returning_is_fetched_before_commit(self):
        error = self.run_script('INSERT INTO "001" VALUES (1, "hello") RETURNING id;')
        error.assert_not_called()
        self.assertFalse(self.app.conn.in_transaction)
        self.app.tree_sql.insert.assert_called_once_with("", "end", values=(1,))
        self.app.load_data.assert_called_once()

    def test_error_rolls_back_prior_write(self):
        error = self.run_script('INSERT INTO "001" VALUES (1, "hello"); INSERT INTO "001" VALUES (1, "duplicate");')
        error.assert_called_once()
        self.assertFalse(self.app.conn.in_transaction)
        self.assertEqual(self.app.conn.execute('SELECT * FROM "001"').fetchall(), [])
        self.app.load_data.assert_not_called()

    def test_commit_error_rolls_back(self):
        self.app.conn.execute("PRAGMA foreign_keys=ON")
        self.app.conn.execute("CREATE TABLE parent (id PRIMARY KEY)")
        self.app.conn.execute("CREATE TABLE child (id REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)")
        error = self.run_script("INSERT INTO child VALUES (42); SELECT * FROM child;")
        error.assert_called_once()
        self.assertFalse(self.app.conn.in_transaction)
        self.assertEqual(self.app.conn.execute("SELECT * FROM child").fetchall(), [])
        self.app.load_data.assert_not_called()

    def test_write_without_result_commits_and_reloads(self):
        error = self.run_script('INSERT INTO "001" VALUES (1, "hello");')
        error.assert_not_called()
        self.assertFalse(self.app.conn.in_transaction)
        self.app.load_data.assert_called_once()


if __name__ == "__main__":
    unittest.main()
