import sqlite3
import tempfile
import unittest
from pathlib import Path

from db import (
    add_card,
    add_column,
    authenticate_user,
    close_db_connection,
    create_board_for_user,
    create_session,
    create_user,
    delete_session,
    get_db_connection,
    get_db_path,
    get_session_user,
    hash_session_token,
    rename_column,
    reorder_cards,
    reorder_columns,
)


class DatabaseSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "kanban.db"
        close_db_connection()
        import os

        os.environ["KANBAN_DB_PATH"] = str(self.db_path)

    def tearDown(self) -> None:
        close_db_connection()
        import os

        os.environ.pop("KANBAN_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_initialization_creates_relational_tables_idempotently(self) -> None:
        conn = get_db_connection()
        self.assertTrue(get_db_path().exists())

        # Calling again validates idempotent schema initialization.
        conn_again = get_db_connection()
        self.assertIsNotNone(conn_again)

        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in rows}

        self.assertIn("users", table_names)
        self.assertIn("boards", table_names)
        self.assertIn("columns", table_names)
        self.assertIn("cards", table_names)
        self.assertIn("sessions", table_names)

    def test_username_unique_password_hashed_and_one_board_per_user(self) -> None:
        user_id = create_user("user", "password")
        self.assertGreater(user_id, 0)
        row = get_db_connection().execute(
            "SELECT password FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        self.assertNotEqual(row["password"], "password")
        self.assertEqual(authenticate_user("user", "password"), user_id)

        with self.assertRaises(sqlite3.IntegrityError):
            create_user("user", "password")

        board_id = create_board_for_user(user_id, "Main board")
        self.assertGreater(board_id, 0)

        with self.assertRaises(sqlite3.IntegrityError):
            create_board_for_user(user_id, "Second board")

    def test_session_can_be_created_loaded_and_deleted(self) -> None:
        user_id = create_user("session-user", "password")
        token, expires_at = create_session(user_id)

        self.assertTrue(token)
        self.assertTrue(expires_at)
        stored = get_db_connection().execute("SELECT token FROM sessions").fetchone()
        self.assertEqual(stored["token"], hash_session_token(token))
        self.assertNotEqual(stored["token"], token)

        row = get_session_user(token)
        self.assertIsNotNone(row)
        self.assertEqual(row["username"], "session-user")

        delete_session(token)
        self.assertIsNone(get_session_user(token))

    def test_legacy_plaintext_password_is_upgraded_on_initialization(self) -> None:
        conn = get_db_connection()
        with conn:
            conn.execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                ("legacy", "plaintext", "2026-01-01T00:00:00+00:00"),
            )

        close_db_connection()
        conn = get_db_connection()
        row = conn.execute(
            "SELECT password FROM users WHERE username = ?",
            ("legacy",),
        ).fetchone()

        self.assertNotEqual(row["password"], "plaintext")
        self.assertIsNotNone(authenticate_user("legacy", "plaintext"))

    def test_legacy_raw_session_token_is_upgraded_on_initialization(self) -> None:
        user_id = create_user("legacy-session", "password")
        raw_token = "legacy-raw-session-token"
        conn = get_db_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO sessions (token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    raw_token,
                    user_id,
                    "2026-01-01T00:00:00+00:00",
                    "2099-01-01T00:00:00+00:00",
                ),
            )

        close_db_connection()
        conn = get_db_connection()
        stored = conn.execute("SELECT token FROM sessions WHERE user_id = ?", (user_id,)).fetchone()

        self.assertEqual(stored["token"], hash_session_token(raw_token))
        self.assertIsNotNone(get_session_user(raw_token))

    def test_columns_can_be_renamed_and_reordered_by_position(self) -> None:
        user_id = create_user("alice", "password")
        board_id = create_board_for_user(user_id)
        conn = get_db_connection()
        with conn:
            conn.execute("DELETE FROM cards WHERE column_id IN (SELECT id FROM \"columns\" WHERE board_id = ?)", (board_id,))
            conn.execute("DELETE FROM \"columns\" WHERE board_id = ?", (board_id,))

        col_a = add_column(board_id, "To Do")
        col_b = add_column(board_id, "Doing")
        col_c = add_column(board_id, "Done")

        rename_column(col_b, "In progress")
        reorder_columns(board_id, [col_c, col_a, col_b])

        conn = get_db_connection()
        rows = conn.execute(
            "SELECT id, title, position FROM \"columns\" WHERE board_id = ? ORDER BY position",
            (board_id,),
        ).fetchall()

        self.assertEqual([row["id"] for row in rows], [col_c, col_a, col_b])
        self.assertEqual([row["position"] for row in rows], [0, 1, 2])
        self.assertEqual(rows[2]["title"], "In progress")

    def test_cards_store_required_details_archived_and_position(self) -> None:
        user_id = create_user("bob", "password")
        board_id = create_board_for_user(user_id)
        conn = get_db_connection()
        with conn:
            conn.execute("DELETE FROM cards WHERE column_id IN (SELECT id FROM \"columns\" WHERE board_id = ?)", (board_id,))
            conn.execute("DELETE FROM \"columns\" WHERE board_id = ?", (board_id,))
        column_id = add_column(board_id, "To Do")

        first = add_card(column_id, "Card 1", "")
        second = add_card(column_id, "Card 2", "Details")
        third = add_card(column_id, "Card 3", "More details")

        reorder_cards(column_id, [third, first, second])

        conn = get_db_connection()
        row = conn.execute(
            "SELECT title, details, archived FROM cards WHERE id = ?",
            (first,),
        ).fetchone()
        self.assertEqual(row["title"], "Card 1")
        self.assertEqual(row["details"], "")
        self.assertEqual(row["archived"], 0)

        positions = conn.execute(
            "SELECT id, position FROM cards WHERE column_id = ? ORDER BY position",
            (column_id,),
        ).fetchall()
        self.assertEqual([row["id"] for row in positions], [third, first, second])
        self.assertEqual([row["position"] for row in positions], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
